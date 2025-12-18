import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from GoogleNews import GoogleNews
from newsapi import NewsApiClient
import datetime
import json
import os
import numpy as np

# HELPER FUNCTIONS
def get_stock_data_safe(ticker: str, period: str = "1y"):
    """Mengambil data historis dengan error handling."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return None
        return df
    except Exception:
        return None

def clean_ticker_for_news(ticker: str) -> str:
    """Menghapus suffix .JK atau .T untuk pencarian berita yang lebih baik."""
    return ticker.replace(".JK", "").replace(".jk", "").replace(".T", "")

# INDIVIDUAL TOOLS
def get_stock_price(ticker: str):
    df = get_stock_data_safe(ticker, period='1d')
    if df is None: return "Harga tidak ditemukan."
    return str(df.iloc[-1].Close)

def calculate_SMA(ticker: str, window: int = 20):
    df = get_stock_data_safe(ticker, period='2y')
    if df is None: return "Data tidak cukup."
    return str(df['Close'].rolling(window=window).mean().iloc[-1])

def calculate_EMA(ticker: str, window: int = 20):
    df = get_stock_data_safe(ticker, period='2y')
    if df is None: return "Data tidak cukup."
    return str(df['Close'].ewm(span=window, adjust=False).mean().iloc[-1])

def calculate_RSI(ticker: str, window: int = 14):
    df = get_stock_data_safe(ticker, period='6mo')
    if df is None: return "Data tidak cukup."
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return str(rsi.iloc[-1])

def calculate_MACD(ticker: str):
    df = get_stock_data_safe(ticker, period='1y')
    if df is None: return "Data tidak cukup."
    short_EMA = df['Close'].ewm(span=12, adjust=False).mean()
    long_EMA = df['Close'].ewm(span=26, adjust=False).mean()
    macd_line = short_EMA - long_EMA
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    return f"MACD: {macd_line.iloc[-1]:.2f}, Signal: {signal_line.iloc[-1]:.2f}, Hist: {hist.iloc[-1]:.2f}"

# 3. VISUALIZATION
def plot_interactive_chart(ticker: str):
    """Membuat grafik candlestick interaktif dan menyimpannya di session state."""
    try:
        df = get_stock_data_safe(ticker, period='1y') # Default 1 tahun untuk view swing
        if df is None:
            return f"Gagal membuat grafik untuk {ticker} (data kosong)."

        # SMA
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()

        fig = go.Figure()

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name=ticker
        ))

        # Indikator Trend
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], mode='lines', name='SMA 50', line=dict(color='orange', width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], mode='lines', name='SMA 200', line=dict(color='blue', width=1)))

        fig.update_layout(
            title=f"Analisis Teknikal {ticker.upper()} (1 Tahun)",
            height=500,
            template="plotly_dark",
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis_rangeslider_visible=False
        )
        
        # Simpan chart ke session state
        st.session_state['last_chart'] = fig
        return f"Grafik interaktif (dengan SMA50 & SMA200) untuk {ticker.upper()} telah dibuat."
    except Exception as e:
        return f"Terjadi error saat membuat grafik: {e}"


# 4. HYBRID NEWS ENGINE (Google News + NewsAPI)
def get_hybrid_news(ticker: str) -> str:
    """
    Menggabungkan berita dari Google News (Lokal/Indo) dan NewsAPI (Global).
    """
    news_results = []
    clean_symbol = clean_ticker_for_news(ticker)
    
    # Google News
    try:
        # indonesian news
        googlenews = GoogleNews(lang='id', region='ID')
        googlenews.search(f"Saham {clean_symbol}")
        g_results = googlenews.result()
        
        for item in g_results[:3]: # Ambil 3 teratas
            title = item.get('title', '')
            date = item.get('date', '')
            link = item.get('link', '')
            if title:
                news_results.append(f"[GoogleNews] {date}: {title} ({link})")
    except Exception as e:
        print(f"Google News Error: {e}")

    # NewsAPI (US)
    api_key = os.getenv("NEWS_API_KEY")
    if api_key:
        try:
            newsapi = NewsApiClient(api_key=api_key)
            # berita saham
            response = newsapi.get_everything(
                q=clean_symbol,
                language='en',
                sort_by='relevancy',
                page_size=3
            )
            if response['status'] == 'ok':
                for item in response['articles']:
                    title = item.get('title', '')
                    source = item.get('source', {}).get('name', 'NewsAPI')
                    link = item.get('url', '')
                    if title:
                        news_results.append(f"[{source}] {title} ({link})")
        except Exception as e:
            print(f"NewsAPI Error: {e}")
    
    if not news_results:
        return "Tidak ditemukan berita signifikan dalam 7 hari terakhir."
    
    return "\n\n".join(news_results)

# RECOMMENDATION ENGINE
def analyze_stock_recommendation(ticker: str) -> str:
    """
    TOOL UTAMA: Melakukan perhitungan teknikal 'Hard Math' di Python
    dan mengambil berita, lalu menyusun laporan untuk dianalisis Gemini.
    """
    # 1. Ambil Data
    df = get_stock_data_safe(ticker, period="2y")
    if df is None:
        return f"Gagal mengambil data saham {ticker}. Pastikan simbol benar."

    # 2. Hitung Indikator
    current_price = df['Close'].iloc[-1]
    
    # Trend (SMA)
    sma_50 = df['Close'].rolling(window=50).mean().iloc[-1]
    sma_200 = df['Close'].rolling(window=200).mean().iloc[-1]
    
    trend_major = "BULLISH (Uptrend Kuat)" if current_price > sma_200 else "BEARISH (Downtrend)"
    trend_minor = "Di Atas SMA50" if current_price > sma_50 else "Di Bawah SMA50"

    # Momentum (RSI)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    rsi_status = "NETRAL"
    if rsi > 70: rsi_status = "OVERBOUGHT (Terlalu Mahal -> Potensi Turun)"
    if rsi < 30: rsi_status = "OVERSOLD (Terlalu Murah -> Potensi Naik)"

    # MACD
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    macd_status = "GOLDEN CROSS (Sinyal Beli)" if macd_val > signal_val else "DEAD CROSS (Sinyal Jual/Wait)"

    # 3. Ambil Berita Hybrid
    news_summary = get_hybrid_news(ticker)

    # 4. Susun Laporan untuk LLM
    report = f"""
    === LAPORAN INTELEJEN SAHAM: {ticker.upper()} ===
    
    [DATA TEKNIKAL MENTAH]
    - Harga Terkini: {current_price:,.2f}
    - SMA 200 (Major Trend): {sma_200:,.2f} -> Status: {trend_major}
    - SMA 50 (Mid Trend): {sma_50:,.2f} -> Status: {trend_minor}
    - RSI (14): {rsi:.2f} -> Status: {rsi_status}
    - MACD: {macd_status} (MACD Line: {macd_val:.4f}, Signal: {signal_val:.4f})
    
    [BERITA TERKINI & SENTIMEN]
    {news_summary}
    
    [INSTRUKSI UNTUK AI]
    Sebagai Advisor Swing Trading profesional, berikan analisis mendalam berdasarkan data di atas:
    1. Tentukan Sinyal: BUY, SELL, atau WAIT.
    2. Berikan Skor Keyakinan (0-10).
    3. Jelaskan alasannya menggabungkan Teknikal (Trend/Momentum) dan Sentimen Berita.
    4. Sarankan Strategi Entry (Harga Beli), Stop Loss (Cut Loss), dan Target Profit (Resistance).
    
    PENTING: Selalu sertakan Disclaimer bahwa ini bukan ajakan investasi paksaan.
    """
    return report

# 6. PORTFOLIO & FUNDAMENTAL
def get_fundamental_data(ticker: str):
    try:
        info = yf.Ticker(ticker).info
        return (f"Data Fundamental {ticker.upper()}:\n"
                f"- Market Cap: {info.get('marketCap', 'N/A')}\n"
                f"- P/E Ratio: {info.get('trailingPE', 'N/A')}\n"
                f"- EPS: {info.get('trailingEps', 'N/A')}\n"
                f"- PBV Ratio: {info.get('priceToBook', 'N/A')}")
    except:
        return "Gagal mengambil data fundamental."

def get_my_portfolio():
    """
    Membaca data portofolio dan watchlist pengguna dari file JSON.
    """
    try:
        FILE_PATH = os.path.join("data", "user_data.json")
        
        if not os.path.exists(FILE_PATH) or os.path.getsize(FILE_PATH) == 0:
            return "INFO: Data pengguna kosong."
            
        with open(FILE_PATH, "r") as f:
            data = json.load(f)
        
        portfolio = data.get("portfolio", [])
        watchlist = data.get("watchlist", [])
        
        summary = "DATA PENGGUNA SAAT INI:\n"
        if watchlist:
            summary += f"[Watchlist]: {', '.join(watchlist)}\n"
        if portfolio:
            summary += "[Portofolio]:\n"
            for item in portfolio:
                summary += f"- Saham {item['symbol']}: {item['quantity']} lot (Avg: {item['buy_price']})\n"
                
        return summary
    except Exception as e:
        return f"ERROR sistem saat membaca data: {e}"

def analyze_portfolio_holdings():
    try:
        FILE_PATH = os.path.join("data", "user_data.json")
        
        if not os.path.exists(FILE_PATH) or os.path.getsize(FILE_PATH) == 0:
            return "INFO: Data portofolio kosong. Silakan isi watchlist/portofolio dulu."
            
        with open(FILE_PATH, "r") as f:
            data = json.load(f)
        
        portfolio = data.get("portfolio", [])
        if not portfolio:
            return "Portofolio Anda saat ini kosong."

        # Inisialisasi variabel hitungan
        total_invested = 0
        total_current_value = 0
        details = []

        #LOOPING DI PYTHON
        for item in portfolio:
            symbol = item['symbol']
            qty = float(item['quantity'])
            avg_buy = float(item['buy_price'])
            
            # get harga real-time
            df = get_stock_data_safe(symbol, period="1d")
            
            if df is None or df.empty:
                current_price = avg_buy # Fallback jika error
                remark = "(Gagal ambil harga)"
            else:
                current_price = df['Close'].iloc[-1]
                remark = ""

            # Simple Mathematics
            initial_val = avg_buy * qty
            current_val = current_price * qty
            pnl = current_val - initial_val
            pnl_percent = (pnl / initial_val) * 100 if initial_val != 0 else 0

            total_invested += initial_val
            total_current_value += current_val
            
            # Formatting baris per saham
            sign = "+" if pnl >= 0 else ""
            details.append(
                f"- **{symbol}**: {qty} lot. Beli @ {avg_buy:,.0f} -> Sekarang {current_price:,.0f}. "
                f"P/L: {sign}{pnl:,.0f} ({sign}{pnl_percent:.2f}%) {remark}"
            )

        # Hitungan Total
        total_pnl = total_current_value - total_invested
        total_pnl_percent = (total_pnl / total_invested) * 100 if total_invested != 0 else 0
        sign_total = "+" if total_pnl >= 0 else ""

        # Susun Laporan untuk Gemini
        report = f"""
=== LAPORAN KINERJA PORTOFOLIO (REAL-TIME) ===
[RINCIAN PER SAHAM]
{chr(10).join(details)}

[TOTAL KESELURUHAN]
- Total Modal: {total_invested:,.0f}
- Nilai Sekarang: {total_current_value:,.0f}
- Total Profit/Loss: {sign_total}{total_pnl:,.0f} ({sign_total}{total_pnl_percent:.2f}%)

[INSTRUKSI UNTUK AI]
1. Jelaskan performa portofolio secara keseluruhan (Untung/Rugi).
2. Highlight saham "Winner" (paling untung) dan "Loser" (paling rugi).
3. Berikan saran singkat:
   - Jika untung besar (>10%): Pertimbangkan Take Profit sebagian?
   - Jika rugi besar (<-5%): Apakah perlu Cut Loss atau Average Down (cek fundamental)?
"""
        return report

    except Exception as e:
        return f"Error saat analisis portofolio: {str(e)}"