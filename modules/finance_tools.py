import os
import json
from typing import Optional, Union

import yfinance as yf
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import numpy as np
from GoogleNews import GoogleNews
from newsapi import NewsApiClient

# 1. HELPER FUNCTIONS
def get_stock_data_safe(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Retrieves historical stock data with error handling.
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return None
        return df
    except Exception:
        return None

def clean_ticker_for_news(ticker: str) -> str:
    """
    Sanitizes the ticker symbol by removing exchange suffixes for news searches.
    """
    return ticker.replace(".JK", "").replace(".jk", "").replace(".T", "")

# 2. BASIC TECHNICAL & FUNDAMENTAL TOOLS
def get_stock_price(ticker: str) -> str:
    """Fetches the most recent closing price."""
    df = get_stock_data_safe(ticker, period='1d')
    if df is None: 
        return "Price data not found."
    return str(df.iloc[-1].Close)

def calculate_SMA(ticker: str, window: int = 20) -> str:
    """Calculates the Simple Moving Average (SMA)."""
    df = get_stock_data_safe(ticker, period='2y')
    if df is None: 
        return "Insufficient data."
    return str(df['Close'].rolling(window=window).mean().iloc[-1])

def calculate_EMA(ticker: str, window: int = 20) -> str:
    """Calculates the Exponential Moving Average (EMA)."""
    df = get_stock_data_safe(ticker, period='2y')
    if df is None: 
        return "Insufficient data."
    return str(df['Close'].ewm(span=window, adjust=False).mean().iloc[-1])

def calculate_RSI(ticker: str, window: int = 14) -> str:
    """Calculates the Relative Strength Index (RSI)."""
    df = get_stock_data_safe(ticker, period='6mo')
    if df is None: 
        return "Insufficient data."
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return str(rsi.iloc[-1])

def calculate_MACD(ticker: str) -> str:
    """Calculates MACD, Signal, and Histogram values."""
    df = get_stock_data_safe(ticker, period='1y')
    if df is None: 
        return "Insufficient data."
    
    short_EMA = df['Close'].ewm(span=12, adjust=False).mean()
    long_EMA = df['Close'].ewm(span=26, adjust=False).mean()
    macd_line = short_EMA - long_EMA
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    
    return (f"MACD: {macd_line.iloc[-1]:.2f}, "
            f"Signal: {signal_line.iloc[-1]:.2f}, "
            f"Hist: {hist.iloc[-1]:.2f}")

def get_fundamental_data(ticker: str) -> str:
    """
    Retrieves key fundamental metrics (Market Cap, P/E, EPS, PBV).
    """
    try:
        info = yf.Ticker(ticker).info
        return (f"Data Fundamental {ticker.upper()}:\n"
                f"- Market Cap: {info.get('marketCap', 'N/A')}\n"
                f"- P/E Ratio: {info.get('trailingPE', 'N/A')}\n"
                f"- EPS: {info.get('trailingEps', 'N/A')}\n"
                f"- PBV Ratio: {info.get('priceToBook', 'N/A')}")
    except Exception:
        return "Failed to retrieve fundamental data."

# 3. VISUALIZATION
def plot_interactive_chart(ticker: str) -> str:
    """
    Generates and caches an interactive technical analysis chart (Plotly).
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

# 4. NEWS & SENTIMENT ANALYSIS TOOLS
def get_hybrid_news(ticker: str) -> str:
    """
    Aggregates news from Google News (Local) and NewsAPI (Global).
    """
    news_results = []
    clean_symbol = clean_ticker_for_news(ticker)
    
    # Source 1: Google News (Priority: Local/ID)
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

    # Source 2: NewsAPI (Priority: Global/US)
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
        return "No significant news found in the last 7 days."
    
    return "\n\n".join(news_results)

def analyze_news_relevance(ticker: str, topic: Optional[str] = None) -> str:
    """
    Fetches news and uses the configured LLM to perform sentiment analysis.
    """
    # LAZY IMPORT
    from modules.gemini_utils import load_gemini_model

    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        return "Error: Missing NEWS_API_KEY in environment variables."

    try:
        newsapi = NewsApiClient(api_key=news_api_key)
        
        # Resolve full company name for better search relevance
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
            return f"No relevant news found for {company_name}."

        news_context = []
        for i, item in enumerate(articles, 1):
            title = item.get('title', 'No Title')
            desc = item.get('description', 'No Description')
            link = item.get('url', '#')
            news_context.append(f"📰 **{i}. {title}**\n\n{desc}\n\n🔗 [Read More]({link})\n")

        formatted_news = "\n---\n".join(news_context)
        
        # Load LLM for stateless analysis
        model = load_gemini_model()
        analysis_prompt = (
            f"Analyze the following news for {ticker.upper()} ({company_name}). "
            f"Summarize key findings and determine the general sentiment (Positive/Negative/Neutral).\n\n"
            f"{formatted_news}"
        )
        
        response = model.generate_content(analysis_prompt)
        return response.text

    except Exception as e:
        if 'apiKeyInvalid' in str(e):
            return "❌ Error: Invalid NewsAPI Key."
        return f"Error fetching news analysis: {str(e)}"

# 5. ADVANCED ANALYSIS TOOLS (LOGIKA ASLI ANDA)
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
    
    # Force Chart Generation
    plot_interactive_chart(ticker)

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

# 6. PORTFOLIO TOOLS
def get_my_portfolio() -> str:
    """Reads raw portfolio data from local JSON storage."""
    try:
        FILE_PATH = os.path.join("data", "user_data.json")
        if not os.path.exists(FILE_PATH): 
            return "Data is empty."
        with open(FILE_PATH, "r") as f:
            data = json.load(f)
        return str(data.get("portfolio", []))
    except Exception: 
        return "Error reading data."