import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import json
import os

# Tools Analisis Teknikal & Fundamental

def get_stock_price(ticker: str):
    history = yf.Ticker(ticker).history(period='1d')
    if history.empty: return "N/A"
    return str(history.iloc[-1].Close)

def calculate_SMA(ticker: str, window: int = 20):
    data = yf.Ticker(ticker).history(period='1y').Close
    return str(data.rolling(window=window).mean().iloc[-1])

def calculate_EMA(ticker: str, window: int = 20):
    data = yf.Ticker(ticker).history(period='1y').Close
    return str(data.ewm(span=window, adjust=False).mean().iloc[-1])

def calculate_RSI(ticker: str, window: int = 14):
    data = yf.Ticker(ticker).history(period='1y').Close
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=window-1, adjust=False).mean()
    ema_down = down.ewm(com=window-1, adjust=False).mean()
    rs = ema_up / ema_down
    rsi = 100 - (100 / (1 + rs))
    return str(rsi.iloc[-1])

def calculate_MACD(ticker: str):
    data = yf.Ticker(ticker).history(period='1y').Close
    short_EMA = data.ewm(span=12, adjust=False).mean()
    long_EMA = data.ewm(span=26, adjust=False).mean()
    MACD = short_EMA - long_EMA
    signal = MACD.ewm(span=9, adjust=False).mean()
    hist = MACD - signal
    return f"MACD: {MACD.iloc[-1]:.2f}, Signal: {signal.iloc[-1]:.2f}, Hist: {hist.iloc[-1]:.2f}"

def plot_interactive_chart(ticker: str):
    """Membuat grafik candlestick interaktif dan menyimpannya di session state."""
    try:
        data = yf.Ticker(ticker).history(period='6mo') # 6 bulan cukup untuk chat
        if data.empty:
            return f"Gagal membuat grafik untuk {ticker} (data kosong)."

        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name=ticker
        )])
        
        fig.update_layout(
            title=f"Grafik Harga {ticker.upper()} (6 Bulan Terakhir)",
            height=400,
            template="plotly_dark",
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        # Simpan chart ke session state
        st.session_state['last_chart'] = fig
        return f"Grafik interaktif untuk {ticker.upper()} telah dibuat. Silakan lihat di bawah."
    except Exception as e:
        return f"Terjadi error saat membuat grafik: {e}"

def get_fundamental_data(ticker: str):
    try:
        info = yf.Ticker(ticker).info
        return (f"Data Fundamental {ticker.upper()}:\n"
                f"- Market Cap: {info.get('marketCap', 'N/A'):,}\n"
                f"- P/E Ratio: {info.get('trailingPE', 'N/A')}\n"
                f"- EPS: {info.get('trailingEps', 'N/A')}")
    except:
        return "Gagal mengambil data fundamental."

def get_my_portfolio():
    """
    Membaca data portofolio dan watchlist pengguna dari file JSON.
    """
    try:
        FILE_PATH = os.path.join("data", "user_data.json")
        
        if not os.path.exists(FILE_PATH) or os.path.getsize(FILE_PATH) == 0:
            return "INFO: Data pengguna kosong. Beritahu pengguna untuk menambahkan saham di halaman Watchlist terlebih dahulu."
            
        with open(FILE_PATH, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return "ERROR: File data pengguna rusak (corrupt). Sarankan reset di halaman Watchlist."
            
        portfolio = data.get("portfolio", [])
        watchlist = data.get("watchlist", [])
        
        if not portfolio and not watchlist:
             return "INFO: Watchlist dan Portofolio pengguna saat ini masih KOSONG."

        # 2. Format data menjadi teks
        summary = "DATA PENGGUNA SAAT INI:\n"
        
        if watchlist:
            summary += f"[Watchlist]: {', '.join(watchlist)}\n"
            
        if portfolio:
            summary += "[Portofolio]:\n"
            for item in portfolio:
                summary += f"- Saham {item['symbol']}: {item['quantity']} lot (Harga Beli Avg: ${item['buy_price']})\n"
                
        return summary

    except Exception as e:
        return f"ERROR sistem saat membaca data: {e}"