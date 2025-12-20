import streamlit as st
import pandas as pd

# Import Model (Business Logic)
from modules.stock_tools import get_stock_data_safe, yahoo_status, get_batch_stock_data
from modules.news_tools import get_latest_news

# Import View (Presentation Logic)
import modules.dashboard_view as view

# =====================================================
# 🚀 CONTROLLER: DASHBOARD
# =====================================================
def show_dashboard():
    """
    Main Controller Function.
    Orchestrates the data flow: Fetch Data (Model) -> Render UI (View).
    """
    
    # 1. Initialize View
    view.render_global_styles()

    # 2. Process Ticker Data
    ticker_symbols = {
        "AAPL": "Apple", "TSLA": "Tesla", "NVDA": "NVIDIA",
        "GOOGL": "Google", "AMZN": "Amazon",
        "BTC-USD": "Bitcoin", "GC=F": "Gold", "EURUSD=X": "Euro/USD"
    }
    
    processed_tickers = []
    for symbol, name in ticker_symbols.items():
        try:
            data = get_stock_data_safe(symbol, period="5d")
            if len(data) >= 2:
                latest = data["Close"].iloc[-1]
                prev = data["Close"].iloc[-2]
                change = ((latest - prev) / prev) * 100
                processed_tickers.append({
                    "name": name,
                    "value": latest,
                    "change": change
                })
        except Exception:
            continue
            
    view.render_ticker_bar(processed_tickers, yahoo_status())

    # 3. Process News Data
    news_raw = get_latest_news()
    processed_news = []
    
    if news_raw and "articles" in news_raw:
        for article in news_raw["articles"][:4]:
            processed_news.append({
                "title": article.get("title", "No Title"),
                "desc": (article.get("description", "") or "")[:150] + "...",
                "source": article.get("source", {}).get("name", "Unknown"),
                "url": article.get("url", "#"),
                "published": article.get("publishedAt", "")[:10]
            })
            
    view.render_news_section(processed_news)

    # 4. Process Weekly Movers (Logic Only)
    candidate_stocks = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT", "META", "NFLX"]
    batch_data = get_batch_stock_data(candidate_stocks, period="1mo")
    trending_scores = []
    
    if not batch_data.empty:
        for ticker in candidate_stocks:
            try:
                # Handle MultiIndex logic properly
                if isinstance(batch_data.columns, pd.MultiIndex):
                    stock_data = batch_data[ticker].copy() if ticker in batch_data.columns.levels[0] else pd.DataFrame()
                else:
                    stock_data = batch_data.copy()

                if not stock_data.empty and len(stock_data) >= 7:
                    latest = stock_data["Close"].iloc[-1]
                    prev_week = stock_data["Close"].iloc[-7]
                    delta = ((latest - prev_week) / prev_week) * 100
                    trending_scores.append((ticker, delta, stock_data))
            except Exception:
                continue

    top_trending = sorted(trending_scores, key=lambda x: x[1], reverse=True)[:4] if trending_scores else []
    
    # 5. Render Weekly Movers
    view.render_weekly_movers(top_trending)

    # 6. Render Footer
    view.render_footer()