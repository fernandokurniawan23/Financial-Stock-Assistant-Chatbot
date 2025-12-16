import os
import sqlite3
import streamlit as st
import yfinance as yf
from typing import List, Dict, Optional, Any
from newsapi import NewsApiClient
import google.generativeai as genai

# Local modules
from modules.stock_tools import get_stock_data_safe, yahoo_status
from modules.gemini_utils import load_gemini_model
from modules.finance_tools import (
    get_stock_price, calculate_SMA, calculate_EMA,
    calculate_RSI, calculate_MACD, plot_interactive_chart,
    get_fundamental_data, get_my_portfolio
)

# Constants
DB_FILE = 'chat_history.db'
ROLE_MODEL = 'model'      # Role untuk Gemini API
ROLE_USER = 'user'        # Role untuk User
ROLE_ASSISTANT = 'assistant' # Role untuk UI Streamlit

def init_db() -> None:
    """
    Menginisialisasi database SQLite dengan skema yang dibutuhkan.
    Membuat tabel 'chat_logs' jika belum tersedia.
    """
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def save_chat_log(role: str, content: str) -> None:
    """
    Menyimpan pesan chat ke database SQLite.

    Args:
        role (str): Asal pesan (ROLE_USER atau ROLE_MODEL).
        content (str): Isi pesan teks.
    """
    # Mapping role agar konsisten di database
    db_role = ROLE_USER if role == ROLE_USER else ROLE_MODEL
    
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO chat_logs (role, content) VALUES (?, ?)', 
            (db_role, content)
        )
        conn.commit()

def load_chat_history_for_gemini() -> List[Dict[str, Any]]:
    """
    Mengambil riwayat chat dari database dan memformatnya untuk Gemini API.

    Returns:
        List[Dict[str, Any]]: List berisi dictionary dengan format 
                              [{'role': 'user', 'parts': [...]}, ...].
    """
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT role, content FROM chat_logs ORDER BY id ASC')
        data = cursor.fetchall()
    
    return [{"role": role, "parts": [content]} for role, content in data]

def clear_db() -> None:
    """Menghapus seluruh data (truncate) pada tabel chat_logs."""
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM chat_logs')
        conn.commit()

def analyze_news_relevance(ticker: str, topic: Optional[str] = None) -> str:
    """
    Mengambil dan menganalisis sentimen berita menggunakan NewsAPI dan Gemini.

    Args:
        ticker (str): Simbol saham (contoh: 'BBCA').
        topic (Optional[str]): Topik spesifik untuk filter berita. Default None.

    Returns:
        str: Ringkasan sentimen yang dihasilkan oleh AI.
    """
    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        return "❌ Error: Missing NEWS_API_KEY in environment variables."

    try:
        newsapi = NewsApiClient(api_key=news_api_key)
        
        # Mencoba mendapatkan nama panjang perusahaan untuk hasil search lebih baik
        try:
            company_name = yf.Ticker(ticker).info.get('longName', ticker)
        except Exception:
            company_name = ticker

        query = f'"{company_name}" AND "{topic}"' if topic else f'"{company_name}"'
        
        news = newsapi.get_everything(
            q=query, 
            language='en', 
            sort_by='relevancy', 
            page_size=5
        )
        
        articles = news.get('articles')
        if not articles:
            return f"Tidak ada berita relevan untuk {company_name}."

        news_context = []
        for i, item in enumerate(articles, 1):
            title = item.get('title', 'No Title')
            desc = item.get('description', 'No Description')
            link = item.get('url', '#')
            news_context.append(f"📰 **{i}. {title}**\n\n{desc}\n\n🔗 [Baca selengkapnya]({link})\n")

        formatted_news = "\n---\n".join(news_context)
        
        # Load model instance baru untuk analisis one-off (stateless)
        model = load_gemini_model()
        analysis_prompt = (
            f"Analisis berita berikut untuk {ticker.upper()} ({company_name}). "
            f"Ringkas temuan utama dan tentukan sentimen umumnya (Positif/Negatif/Netral).\n\n"
            f"{formatted_news}"
        )
        
        response = model.generate_content(analysis_prompt)
        return response.text

    except Exception as e:
        if 'apiKeyInvalid' in str(e):
            return "❌ Error: Invalid NewsAPI Key."
        return f"Error fetching news: {str(e)}"

def show_chatbot() -> None:
    """
    Fungsi utama (Main Controller) untuk halaman Chatbot.
    Menangani rendering UI, manajemen state, interaksi Gemini, dan persistensi grafik.
    """
    st.title("💬 Stock Analysis Chatbot Assistant")
    
    # Setup awal Database
    init_db()

    # Load Model
    model = load_gemini_model()

    # --- 1. Inisialisasi History UI (Lokal Session) ---
    # Kita butuh ini untuk menyimpan Chart Object yang tidak bisa disimpan di SQLite
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
        # Load history teks dari DB ke UI saat pertama kali buka
        db_history = load_chat_history_for_gemini()
        for msg in db_history:
            # Mapping role Gemini ke Streamlit UI
            role = ROLE_ASSISTANT if msg["role"] == ROLE_MODEL else ROLE_USER
            st.session_state.messages.append({
                "role": role,
                "content": msg["parts"][0],
                "chart": None # Placeholder untuk grafik (kosong karena dari DB)
            })

    # Sidebar / Tombol Utilitas
    col_a, col_b = st.columns([5, 1])
    with col_b:
        if st.button("🗑️ Reset Chat", help="Hapus seluruh riwayat percakapan"):
            clear_db()
            st.session_state.messages = [] # Reset UI history
            if "chat" in st.session_state:
                del st.session_state.chat
            if "last_chart" in st.session_state:
                del st.session_state.last_chart
            st.rerun()

    # Definisi tools
    tools = [
        get_stock_price, calculate_SMA, calculate_EMA,
        calculate_RSI, calculate_MACD, plot_interactive_chart,
        get_fundamental_data, analyze_news_relevance, get_my_portfolio
    ]
    available_functions = {f.__name__: f for f in tools}

    # Inisialisasi Sesi Chat Gemini (Backend Logic)
    if "chat" not in st.session_state:
        db_history_gemini = load_chat_history_for_gemini()
        
        if db_history_gemini:
             st.session_state.chat = model.start_chat(history=db_history_gemini)
        else:
            # --- UPDATE WELCOME MESSAGE DI SINI ---
            welcome_msg = """👋 **Halo! Saya Asisten Analisis Saham AI.**
            
                Saya siap membantu Anda memantau pasar saham (IDX & US). Berikut beberapa contoh perintah yang bisa Anda coba:

                📊 Analisis Teknikal & Chart:
                1 "Tampilkan grafik interaktif BBCA selama 6 bulan terakhir."
                2 "Hitung RSI dan MACD untuk saham TLKM."
                3 "Berapa SMA 20 dan SMA 50 untuk BMRI?"

                📰 Berita & Sentimen:
                4 "Carikan berita terbaru tentang GOTO dan analisis sentimennya."
                5 "Apa sentimen pasar terhadap sektor perbankan hari ini?"

                💰 Fundamental & Portofolio:
                6 "Tampilkan data fundamental saham ASII."
                7 "Cek performa portofolio saya saat ini."
                """
            
            st.session_state.chat = model.start_chat(history=[])
            
            # Simpan pesan pembuka ke UI dan DB
            st.session_state.messages.append({"role": ROLE_ASSISTANT, "content": welcome_msg, "chart": None})
            save_chat_log(ROLE_MODEL, welcome_msg)

    # Navigasi
    if st.button("🏠 Kembali ke Dashboard"):
        st.session_state.active_page = "Dashboard"
        st.rerun()

    # --- 2. Render History Chat (LOOP UTAMA) ---
    # Kita merender dari st.session_state.messages, bukan dari st.session_state.chat.history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Jika pesan ini memiliki grafik yang tersimpan, tampilkan!
            if msg.get("chart"):
                 st.plotly_chart(msg["chart"], use_container_width=True)

    # --- 3. Handler Input User ---
    if prompt := st.chat_input("Tanyakan sesuatu tentang saham..."):
        
        # Tampilkan & Simpan Pesan User
        with st.chat_message(ROLE_USER):
            st.markdown(prompt)
        
        st.session_state.messages.append({"role": ROLE_USER, "content": prompt, "chart": None})
        save_chat_log(ROLE_USER, prompt)

        try:
            # Kirim ke Gemini
            response = st.session_state.chat.send_message(prompt, tools=tools)

            if not response or not response.parts:
                st.error("⚠️ Tidak ada respon dari model.")
                st.stop()

            first_part = response.parts[0]

            # --- Skenario A: Function Calling ---
            if hasattr(first_part, "function_call") and first_part.function_call:
                fc = first_part.function_call
                tool_name = fc.name
                tool_args = dict(fc.args)

                # Casting tipe data
                if "window" in tool_args:
                    tool_args["window"] = int(tool_args["window"])

                func = available_functions.get(tool_name)
                
                if func:
                    with st.spinner(f"Menjalankan {tool_name}..."):
                        try:
                            # Eksekusi fungsi Python
                            result = func(**tool_args)

                            # Kirim hasil fungsi kembali ke Gemini
                            final_res = st.session_state.chat.send_message(
                                genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=tool_name, 
                                        response={"content": result}
                                    )
                                )
                            )
                            
                            # Ambil jawaban akhir teks
                            answer_text = final_res.parts[0].text
                            
                            # Cek apakah ada grafik baru yang dibuat oleh fungsi?
                            # Kita asumsikan fungsi 'plot_interactive_chart' memperbarui st.session_state.last_chart
                            current_chart = None
                            if tool_name == "plot_interactive_chart" and "last_chart" in st.session_state:
                                current_chart = st.session_state.last_chart

                            # Render Jawaban Akhir + Grafik
                            with st.chat_message(ROLE_ASSISTANT):
                                st.markdown(answer_text)
                                if current_chart:
                                    st.plotly_chart(current_chart, use_container_width=True)
                            
                            # Simpan ke Session UI (Agar persist saat rerun)
                            st.session_state.messages.append({
                                "role": ROLE_ASSISTANT, 
                                "content": answer_text,
                                "chart": current_chart # PENTING: Simpan objek grafik di sini
                            })
                            
                            # Simpan Text ke DB (Grafik tidak bisa disimpan ke DB SQLite standar)
                            save_chat_log(ROLE_MODEL, answer_text)

                        except Exception as e:
                            error_msg = f"Error saat eksekusi {tool_name}: {str(e)}"
                            st.error(error_msg)
                            save_chat_log(ROLE_MODEL, error_msg)
                            st.session_state.messages.append({"role": ROLE_ASSISTANT, "content": error_msg, "chart": None})
                else:
                    st.warning(f"⚠️ Fungsi '{tool_name}' belum diimplementasikan.")

            # --- Skenario B: Teks Biasa ---
            else:
                text_resp = getattr(first_part, "text", None)
                if text_resp:
                    with st.chat_message(ROLE_ASSISTANT):
                        st.markdown(text_resp)
                    
                    st.session_state.messages.append({"role": ROLE_ASSISTANT, "content": text_resp, "chart": None})
                    save_chat_log(ROLE_MODEL, text_resp)
                else:
                    st.warning("🤔 Model tidak memberikan respons teks.")

        except Exception as e:
            st.error(f"System Error: {str(e)}")