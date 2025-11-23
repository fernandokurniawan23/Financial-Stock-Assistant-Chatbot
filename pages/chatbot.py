import streamlit as st
from modules.stock_tools import get_stock_data_safe, yahoo_status
from google import generativeai as genai
from modules.gemini_utils import load_gemini_model
from modules.finance_tools import (
    get_stock_price, calculate_SMA, calculate_EMA,
    calculate_RSI, calculate_MACD, plot_interactive_chart,
    get_fundamental_data, get_my_portfolio
)
from newsapi import NewsApiClient
import os

# Inisialisasi model Gemini
model = load_gemini_model()

def analyze_news_relevance(ticker: str, topic: str = None):
    """Menganalisis berita relevan dari NewsAPI untuk ticker & topik tertentu."""
    try:
        news_api_key = os.getenv("NEWS_API_KEY")
        if not news_api_key:
            return "❌ Error: Variabel NEWS_API_KEY tidak ditemukan di file .env Anda."
        
        newsapi = NewsApiClient(api_key=news_api_key)
        company_name = yf.Ticker(ticker).info.get('longName', ticker)

        if topic:
            query = f'"{company_name}" AND "{topic}"'
            desc = f"dengan topik: '{topic}'"
        else:
            query = f'"{company_name}"'
            desc = "secara umum"

        news = newsapi.get_everything(q=query, language='en', sort_by='relevancy', page_size=5)
        articles = news.get('articles')
        if not articles:
            return f"Tidak ada berita relevan ditemukan untuk {company_name} {desc}."

        news_context = ""
        for i, item in enumerate(articles):
            title = item.get('title', 'Tidak ada judul')
            desc = item.get('description', 'Tidak ada deskripsi')
            link = item.get('url', '#')
            news_context += f"📰 **{i+1}. {title}**\n\n{desc}\n\n🔗 [Baca selengkapnya]({link})\n\n---\n"

        analysis_prompt = f"""
        Anda adalah seorang analis keuangan. Analisis kumpulan berita berikut untuk saham {ticker.upper()} ({company_name}).
        Ringkas temuan utamanya dan jelaskan sentimen umum (positif, negatif, atau netral).

        Berikut datanya:
        {news_context}
        """
        response = model.generate_content(analysis_prompt)
        return response.text

    except Exception as e:
        if 'apiKeyInvalid' in str(e):
            return "❌ Error: API Key NewsAPI tidak valid."
        return f"Terjadi kesalahan saat mengambil berita: {e}"


# Fungsi utama chatbot
def show_chatbot():
    st.title("💬 Stock Analysis Chatbot Assistant")

    tools = [
        get_stock_price, calculate_SMA, calculate_EMA,
        calculate_RSI, calculate_MACD, plot_interactive_chart,
        get_fundamental_data, analyze_news_relevance, get_my_portfolio
    ]
    available_functions = {f.__name__: f for f in tools}

    # Inisialisasi sesi chat
    if "chat" not in st.session_state:
        welcome_message = """
        Halo! Saya adalah Asisten Analisis Saham Anda.

        Anda bisa meminta saya untuk menganalisis saham dengan contoh seperti:
        - "Berapa harga saham TSLA saat ini?"
        - "Hitung SMA 20 hari untuk NVDA"
        - "Tampilkan grafik saham GOOGL"
        - "Analisis berita terbaru tentang AAPL"
        - "Bagaimana kondisi portofolio saya?"
        """
        st.session_state.chat = model.start_chat(history=[{
            "role": "model", "parts": [welcome_message]
        }])

    if st.button("🏠 Kembali ke Dashboard"):
        st.session_state.active_page = "Dashboard"
        st.rerun()

    # Tampilkan grafik terakhir jika ada
    if "last_chart" in st.session_state and st.session_state.last_chart is not None:
        with st.expander("📊 Grafik Terakhir", expanded=True):
            st.plotly_chart(st.session_state.last_chart, use_container_width=True)

    # Riwayat chat
    for msg in st.session_state.chat.history:
        role = "assistant" if msg.role == "model" else msg.role
        if msg.parts and hasattr(msg.parts[0], "text") and msg.parts[0].text:
            with st.chat_message(role):
                st.markdown(msg.parts[0].text)

    # Input chat
    if prompt := st.chat_input("Tanyakan sesuatu tentang saham..."):
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            response = st.session_state.chat.send_message(prompt, tools=tools)

            if response is None or not hasattr(response, "parts") or response.parts is None:
                safe = st.session_state.chat.send_message(prompt)
                with st.chat_message("assistant"):
                    st.markdown(getattr(safe.parts[0], "text", "⚠️ Saya belum bisa memahami pertanyaan Anda."))
                st.stop()

            first_part = response.parts[0] if len(response.parts) > 0 else None
            if first_part is None:
                safe = st.session_state.chat.send_message(prompt)
                with st.chat_message("assistant"):
                    st.markdown(getattr(safe.parts[0], "text", "⚠️ Mohon ulangi pertanyaan Anda."))
                st.stop()

            # Jika model memanggil fungsi
            if hasattr(first_part, "function_call") and first_part.function_call is not None:
                fc = first_part.function_call
                tool_name = fc.name
                tool_args = dict(fc.args)

                function_to_call = available_functions.get(tool_name)
                if function_to_call:
                    if "window" in tool_args:
                        tool_args["window"] = int(tool_args["window"])

                    try:
                        result = function_to_call(**tool_args)

                        final_response = st.session_state.chat.send_message(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=tool_name, response={"content": result}
                                )
                            )
                        )

                        with st.chat_message("assistant"):
                            st.markdown(final_response.parts[0].text)
                            if tool_name == "plot_interactive_chart" and "last_chart" in st.session_state:
                                st.plotly_chart(st.session_state.last_chart, use_container_width=True)

                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat menjalankan fungsi {tool_name}: {e}")
                else:
                    with st.chat_message("assistant"):
                        st.warning(f"⚠️ Fungsi '{tool_name}' tidak ditemukan.")

            # ika model hanya menjawab teks
            else:
                text_response = getattr(first_part, "text", None)
                with st.chat_message("assistant"):
                    if text_response:
                        st.markdown(text_response)
                    else:
                        st.warning("🤔 Saya belum yakin maksud pertanyaan Anda. Bisa tolong diperjelas?")

        except TypeError as e:
            if "NoneType" in str(e):
                safe = st.session_state.chat.send_message(prompt)
                with st.chat_message("assistant"):
                    st.markdown(getattr(safe.parts[0], "text", "⚠️ Mohon ulangi pertanyaan Anda."))
            else:
                st.error(f"Terjadi kesalahan internal: {e}")

        except Exception as e:
            st.error(f"Terjadi kesalahan tak terduga: {e}")
