import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from GoogleNews import GoogleNews
from newsapi import NewsApiClient
import os
import json
import numpy as np

# 1. HELPER FUNCTIONS
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
    """Menghapus suffix .JK atau .T untuk pencarian berita."""
    return ticker.replace(".JK", "").replace(".jk", "").replace(".T", "")

# 2. BASIC TECHNICAL & FUNDAMENTAL TOOLS
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

def get_fundamental_data(ticker: str):
    """Mengambil data fundamental dasar (P/E, Market Cap, EPS)."""
    try:
        info = yf.Ticker(ticker).info
        return (f"Data Fundamental {ticker.upper()}:\n"
                f"- Market Cap: {info.get('marketCap', 'N/A')}\n"
                f"- P/E Ratio: {info.get('trailingPE', 'N/A')}\n"
                f"- EPS: {info.get('trailingEps', 'N/A')}\n"
                f"- PBV Ratio: {info.get('priceToBook', 'N/A')}")
    except:
        return "Gagal mengambil data fundamental."

# 3. VISUALIZATION
def plot_interactive_chart(ticker: str) -> str:
    """
    Generates and caches an interactive technical analysis chart.

    Visualizes 6 months of OHLC data combined with Swing Trading indicators:
    SMA 20, SMA 50, and Fibonacci Retracement levels (0.382, 0.5, 0.618) 
    derived from the 90-day high/low range. The resulting Plotly figure 
    is stored in the Streamlit session state for UI persistence.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'BBCA.JK', 'NVDA').

    Returns:
        str: A status message indicating successful generation or an error description.
    """
    try:
        # 1. Data Fetching
        df = get_stock_data_safe(ticker, period='6mo') 
        if df is None:
            return f"Error: Failed to retrieve chart data for {ticker}."

        # 2. Indicator Calculations
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()

        # Fibonacci Calculation (90-day lookback window)
        recent_data = df.tail(90)
        high_price = recent_data['High'].max()
        low_price = recent_data['Low'].min()
        price_range = high_price - low_price
        
        fib_levels = {
            "Fib 0.382": high_price - (price_range * 0.382),
            "Fib 0.500": high_price - (price_range * 0.5),
            "Fib 0.618": high_price - (price_range * 0.618)
        }

        # 3. Figure Construction
        fig = go.Figure()

        # Candlestick Trace
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name=f'{ticker} Price'
        ))

        # Moving Average Traces
        fig.add_trace(go.Scatter(
            x=df.index, y=df['SMA20'], 
            mode='lines', name='SMA 20', 
            line=dict(color='#22c55e', width=1.5)
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df['SMA50'], 
            mode='lines', name='SMA 50', 
            line=dict(color='#ef4444', width=1.5)
        ))

        # Fibonacci Annotations
        # Rendering lines only for the visible chart period
        start_date_fib = df.index[len(df)//2] 
        end_date_fib = df.index[-1]
        colors_fib = {"Fib 0.382": "orange", "Fib 0.500": "yellow", "Fib 0.618": "cyan"}
        
        for level_name, price in fib_levels.items():
            fig.add_shape(type="line",
                x0=start_date_fib, y0=price, x1=end_date_fib, y1=price,
                line=dict(color=colors_fib[level_name], width=1, dash="dot"),
            )
            fig.add_annotation(
                x=end_date_fib, y=price,
                text=f"{level_name}: {price:,.0f}",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(color=colors_fib[level_name], size=10)
            )

        # 4. Layout Configuration
        fig.update_layout(
            title=f"Technical Chart: {ticker.upper()} (SMA 20/50 + Fibonacci)",
            height=550,
            template="plotly_dark",
            margin=dict(l=20, r=80, t=50, b=20),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1, x=0, xanchor="left", yanchor="bottom")
        )
        
        # Cache figure to session state
        st.session_state['last_chart'] = fig
        return f"Chart generated successfully for {ticker.upper()}."
        
    except Exception as e:
        return f"Chart generation error: {str(e)}"

# 4. HYBRID NEWS ENGINE
def get_hybrid_news(ticker: str) -> str:
    """Menggabungkan berita dari Google News (Lokal) dan NewsAPI (Global)."""
    news_results = []
    clean_symbol = clean_ticker_for_news(ticker)
    
    # --- SUMBER 1: Google News (Prioritas Saham Indo) ---
    try:
        googlenews = GoogleNews(lang='id', region='ID')
        googlenews.search(f"Saham {clean_symbol}")
        g_results = googlenews.result()
        
        for item in g_results[:3]: 
            title = item.get('title', '')
            date = item.get('date', '')
            link = item.get('link', '')
            if title:
                news_results.append(f"[GoogleNews] {date}: {title} ({link})")
    except Exception as e:
        print(f"Google News Error: {e}")

    # --- SUMBER 2: NewsAPI (Prioritas Saham US / Cadangan) ---
    api_key = os.getenv("NEWS_API_KEY")
    if api_key:
        try:
            newsapi = NewsApiClient(api_key=api_key)
            response = newsapi.get_everything(q=clean_symbol, language='en', sort_by='relevancy', page_size=3)
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

# 5. ADVANCED ANALYSIS TOOLS (LLM Helpers)
def analyze_stock_recommendation(ticker: str) -> str:
    """
    Generates a comprehensive technical analysis report for swing trading strategies.
    Aggregates Price Action, Trend (MA20/50), Momentum, Fibonacci, and ATR.
    """
    # 1. Data Retrieval
    df = get_stock_data_safe(ticker, period="6mo")
    if df is None:
        return f"Error: Failed to retrieve data for {ticker}. Verify symbol or connectivity."

    # 2. Technical Indicators
    current_price = df['Close'].iloc[-1]
    
    # A. Trend Analysis (MA 20/50)
    sma_20 = df['Close'].rolling(window=20).mean().iloc[-1]
    sma_50 = df['Close'].rolling(window=50).mean().iloc[-1]
    trend_status = "BULLISH" if sma_20 > sma_50 else "BEARISH"
    
    prev_sma_20 = df['Close'].rolling(window=20).mean().iloc[-2]
    prev_sma_50 = df['Close'].rolling(window=50).mean().iloc[-2]
    cross_signal = "None"
    if prev_sma_20 < prev_sma_50 and sma_20 > sma_50: cross_signal = "GOLDEN CROSS"
    elif prev_sma_20 > prev_sma_50 and sma_20 < sma_50: cross_signal = "DEATH CROSS"

    # B. Price Action (Breakout & Pullback)
    high_20 = df['High'].rolling(window=20).max().iloc[-1]
    is_breakout = current_price >= high_20
    breakout_msg = "POTENTIAL BREAKOUT" if is_breakout else "In Range"
    
    dist_to_sma20 = ((current_price - sma_20) / sma_20) * 100
    is_pullback = trend_status == "BULLISH" and -2 <= dist_to_sma20 <= 2
    pullback_msg = "PULLBACK ZONE (Near SMA 20)" if is_pullback else "None"

    # C. Momentum
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    rsi_status = "NEUTRAL"
    if rsi > 70: rsi_status = "OVERBOUGHT"
    if rsi < 30: rsi_status = "OVERSOLD"

    vol_today = df['Volume'].iloc[-1]
    vol_avg_20 = df['Volume'].rolling(window=20).mean().iloc[-1]
    vol_ratio = vol_today / vol_avg_20 if vol_avg_20 > 0 else 0
    vol_status = "SPIKE" if vol_ratio > 1.5 else "NORMAL"

    # D. Fibonacci
    recent_high = df['High'].tail(90).max()
    recent_low = df['Low'].tail(90).min()
    diff = recent_high - recent_low
    fib_618 = recent_high - (diff * 0.618) 
    fib_500 = recent_high - (diff * 0.5)   
    fib_382 = recent_high - (diff * 0.382) 

    # E. Risk (ATR)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    true_range = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1)
    atr = true_range.rolling(14).mean().iloc[-1]
    suggested_sl = current_price - (atr * 2)

    # 3. Sentiment
    news_summary = get_hybrid_news(ticker)

    # 4. Report Construction
    report = f"""
    === TECHNICAL INTELLIGENCE REPORT: {ticker.upper()} ===
    
    1. TREND ANALYSIS (MA 20/50)
       - Price: {current_price:,.2f}
       - Trend: {trend_status} (SMA20: {sma_20:,.0f} | SMA50: {sma_50:,.0f})
       - Cross Signal: {cross_signal}
    
    2. PRICE ACTION
       - Breakout Status: {breakout_msg} (20D High: {high_20:,.0f})
       - Pullback Status: {pullback_msg}
    
    3. MOMENTUM METRICS
       - RSI (14): {rsi:.2f} [{rsi_status}]
       - Volume: {vol_status} ({vol_ratio:.1f}x Avg)
    
    4. FIBONACCI LEVELS (Support/Re-entry Areas)
       - Fib 0.382: {fib_382:,.0f}
       - Fib 0.500: {fib_500:,.0f}
       - Fib 0.618: {fib_618:,.0f}
    
    5. RISK MANAGEMENT (ATR)
       - ATR (14): {atr:,.2f}
       - Suggested Stop Loss (2 ATR): {suggested_sl:,.0f}
       
    6. EXTERNAL SENTIMENT
       {news_summary}
    
    [SYSTEM INSTRUCTION]
    Act as a Senior Swing Trading Analyst. Evaluate the provided technical metrics and news sentiment to formulate a trading recommendation.
    
    Output Requirements:
    1. RECOMMENDATION: [BUY / WAIT / SELL / STRONG BUY]
    2. TECHNICAL RATIONALE: Synthesize Trend, Pattern, and Fibonacci data.
    3. TRADING PLAN:
       - Entry Zone: Specific price range.
       - Stop Loss: Use ATR-based suggestion.
       - Take Profit: Minimum 1:2 Risk-Reward ratio.
    """
    return report

def get_my_portfolio():
    """Membaca data portofolio mentah (Legacy function, fallback)."""
    try:
        FILE_PATH = os.path.join("data", "user_data.json")
        if not os.path.exists(FILE_PATH): return "Data kosong."
        with open(FILE_PATH, "r") as f:
            data = json.load(f)
        return str(data.get("portfolio", []))
    except: return "Error membaca data."

def analyze_portfolio_holdings():
    """
    TOOL KHUSUS: Mengambil data portofolio dari JSON, lalu secara OTOMATIS
    mengambil harga terkini (Real-time) dan menghitung Gain/Loss.
    """
    try:
        FILE_PATH = os.path.join("data", "user_data.json")
        if not os.path.exists(FILE_PATH) or os.path.getsize(FILE_PATH) == 0:
            return "INFO: Data portofolio kosong. Silakan isi watchlist/portofolio dulu."
            
        with open(FILE_PATH, "r") as f:
            data = json.load(f)
        
        portfolio = data.get("portfolio", [])
        if not portfolio:
            return "Portofolio Anda saat ini kosong."

        total_invested_idr, total_val_idr = 0, 0
        total_invested_usd, total_val_usd = 0, 0
        details = []

        for item in portfolio:
            symbol = item['symbol']
            qty = float(item['quantity'])
            avg_buy = float(item['buy_price'])
            currency = item.get('currency', 'USD') # Default USD
            
            # Ambil harga real-time
            df = get_stock_data_safe(symbol, period="1d")
            
            if df is None or df.empty:
                current_price = avg_buy # Fallback
                remark = "(Gagal ambil harga)"
            else:
                current_price = df['Close'].iloc[-1]
                remark = ""

            initial_val = avg_buy * qty
            current_val = current_price * qty
            pnl = current_val - initial_val
            pnl_percent = (pnl / initial_val) * 100 if initial_val != 0 else 0

            # Pisahkan Keranjang
            if currency == 'IDR':
                total_invested_idr += initial_val
                total_val_idr += current_val
                fmt = "Rp {:,.0f}"
            else:
                total_invested_usd += initial_val
                total_val_usd += current_val
                fmt = "$ {:,.2f}"

            sign = "+" if pnl >= 0 else ""
            details.append(
                f"- **{symbol}** ({currency}): Beli {fmt.format(avg_buy)} -> Kini {fmt.format(current_price)}. "
                f"P/L: {sign}{fmt.format(pnl)} ({sign}{pnl_percent:.2f}%) {remark}"
            )

        # Rangkuman Total
        summary_idr = ""
        if total_invested_idr > 0:
            pnl_idr = total_val_idr - total_invested_idr
            pnl_pct_idr = (pnl_idr/total_invested_idr)*100
            summary_idr = f"TOTAL IDR: Invest Rp {total_invested_idr:,.0f} -> Aset Rp {total_val_idr:,.0f} (P/L: {pnl_pct_idr:+.2f}%)"

        summary_usd = ""
        if total_invested_usd > 0:
            pnl_usd = total_val_usd - total_invested_usd
            pnl_pct_usd = (pnl_usd/total_invested_usd)*100
            summary_usd = f"TOTAL USD: Invest ${total_invested_usd:,.2f} -> Aset ${total_val_usd:,.2f} (P/L: {pnl_pct_usd:+.2f}%)"

        report = f"""
=== LAPORAN KINERJA PORTOFOLIO (REAL-TIME) ===

[RINCIAN PER SAHAM]
{chr(10).join(details)}

[TOTAL KESELURUHAN]
{summary_idr}
{summary_usd}

[INSTRUKSI UNTUK AI]
1. Jelaskan performa portofolio secara keseluruhan (Untung/Rugi).
2. Highlight saham "Winner" dan "Loser".
3. Berikan saran singkat (Hold/Sell/Buy More).
"""
        return report

    except Exception as e:
        return f"Error saat analisis portofolio: {str(e)}"