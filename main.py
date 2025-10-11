import os
import re
import matplotlib.pyplot as plt
import streamlit as st
import yfinance as yf
from PIL import Image
from google import generativeai as genai

st.set_page_config(layout="wide", page_title="Stock Analysis Chatbot")

try:
    with open('API_KEY', 'r') as f:
        content = f.read().strip()
        api_key_value = re.sub(r'GEMINI_API_KEY=[\'"]?', '', content).strip().replace('"', '')
    
    genai.configure(api_key=api_key_value)
    model = genai.GenerativeModel(model_name='gemini-2.5-flash')

except Exception as e:
    st.error(f"Gagal inisialisasi Gemini. Pastikan 'API_KEY' terisi benar. Error: {e}")
    st.stop()

def get_stock_price(ticker: str):
    return str(yf.Ticker(ticker).history(period='1y').iloc[-1].Close)

def calculate_SMA(ticker: str, window: int):
    data = yf.Ticker(ticker).history(period='1y').Close
    return str(data.rolling(window=window).mean().iloc[-1])

def calculate_EMA(ticker: str, window: int):
    data = yf.Ticker(ticker).history(period='1y').Close
    return str(data.ewm(span=window, adjust=False).mean().iloc[-1])

def calculate_RSI(ticker: str):
    data = yf.Ticker(ticker).history(period='1y').Close
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down
    return str(100 - (100 / (1 + rs)).iloc[-1])

def calculate_MACD(ticker: str):
    data = yf.Ticker(ticker).history(period='1y').Close
    short_EMA = data.ewm(span=12, adjust=False).mean()
    long_EMA = data.ewm(span=26, adjust=False).mean()
    MACD = short_EMA - long_EMA
    signal = MACD.ewm(span=9, adjust=False).mean()
    MACD_histogram = MACD - signal
    return f'MACD: {MACD.iloc[-1]}, Signal: {signal.iloc[-1]}, Histogram: {MACD_histogram.iloc[-1]}'

def plot_stock_price(ticker: str):
    data = yf.Ticker(ticker).history(period='1y')
    plt.figure(figsize=(10, 5)); plt.plot(data.index, data.Close)
    plt.title(f'{ticker} Stock Price Over Last Year'); plt.xlabel('Date'); plt.ylabel('Stock Price')
    plt.grid(True); plt.savefig('stock.png'); plt.close()
    return f"Plot harga saham untuk {ticker} berhasil disimpan sebagai stock.png."

tools = [get_stock_price, calculate_SMA, calculate_EMA, calculate_RSI, calculate_MACD, plot_stock_price]
available_functions = {func.__name__: func for func in tools}

st.title('📈 Stock Analysis Chatbot Assistant')

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

for message in st.session_state.chat.history:
    role = "assistant" if message.role == "model" else message.role
    if message.parts and hasattr(message.parts[0], 'text') and message.parts[0].text:
        with st.chat_message(role):
            st.markdown(message.parts[0].text)

if prompt := st.chat_input("Tanyakan sesuatu tentang saham..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response = st.session_state.chat.send_message(prompt, tools=tools)

        if response.parts and hasattr(response.parts[0], 'function_call'):
            fc = response.parts[0].function_call
            tool_name = fc.name
            tool_args = dict(fc.args)

            function_to_call = available_functions[tool_name]
            if 'window' in tool_args:
                tool_args['window'] = int(tool_args['window'])

            function_response_data = function_to_call(**tool_args)

            # MENGGUNAKAN KEMBALI METODE 'protos' YANG SUDAH BERHASIL
            final_response = st.session_state.chat.send_message(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=tool_name,
                        response={"content": function_response_data}
                    )
                )
            )
            
            with st.chat_message("assistant"):
                # Di versi baru, akses teks ada di `final_response.parts[0].text`
                st.markdown(final_response.parts[0].text)
                if tool_name == "plot_stock_price":
                    st.image("stock.png", caption=f"Grafik Harga Saham {tool_args['ticker']}")
        else:
            with st.chat_message("assistant"):
                # Di versi baru, akses teks ada di `response.parts[0].text`
                st.markdown(response.parts[0].text)
                
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")