import pandas as pd
from GoogleNews import GoogleNews
from modules.stock_tools import get_stock_data_safe, get_batch_stock_data, yahoo_status
from modules.news_tools import get_latest_news

"""
DASHBOARD MODEL MODULE
----------------------
Responsibility: Business Logic & Data Access.
Fixes: 
1. Google News Tracking Links (Local).
2. Unicode Escape Sequences like \u003d (Global).
3. Direct Backslash Escapes like \= (Global - NEW FIX).
"""

def clean_news_url(url: str) -> str:
    """
    Universal URL Cleaner/Sanitizer.
    Membersihkan URL dari sampah tracking dan encoding yang rusak.
    """
    if not url:
        return "#"
    
    # 1. FIX GLOBAL NEWS: Escape Sequences
    
    # Handle unicode escape \u003d -> =
    url = url.replace("\\u003d", "=")
    # Handle unicode escape \u0026 -> &
    url = url.replace("\\u0026", "&")
    
    # Handle direct backslash escape \= -> =
    url = url.replace("\\=", "=")
    # ========================
    
    # 2. FIX LOCAL NEWS: Google Tracking Params
    if '&ved' in url:
        url = url.split('&ved')[0]
    if '&usg' in url:
        url = url.split('&usg')[0]
        
    # 3. Protocol Check
    if not url.startswith('http'):
        url = f"https://{url}"
        
    return url

def get_system_status() -> str:
    return yahoo_status()

def fetch_ticker_tape_data() -> list:
    ticker_map = {
        "AAPL": "Apple", 
        "NVDA": "NVIDIA",
        "MSFT": "Microsoft",
        "TSLA": "Tesla",
        "AMZN": "Amazon",
        "BBCA.JK": "BCA", 
        "BBRI.JK": "BRI", 
        "BMRI.JK": "Mandiri",
        "TLKM.JK": "Telkom",
        "ASII.JK": "Astra"
    }
    results = []
    for symbol, name in ticker_map.items():
        try:
            df = get_stock_data_safe(symbol, period="5d")
            if df is not None and len(df) >= 2:
                latest = df["Close"].iloc[-1]
                prev = df["Close"].iloc[-2]
                change_pct = ((latest - prev) / prev) * 100
                results.append({
                    "name": name,
                    "symbol": symbol,
                    "value": float(latest),
                    "change": float(change_pct)
                })
        except Exception:
            continue
    return results

def fetch_global_news() -> list:
    news_raw = get_latest_news()
    processed = []
    if news_raw and "articles" in news_raw:
        for article in news_raw["articles"][:4]:
            raw_url = article.get("url", "#")
            # call cleaner
            clean_link = clean_news_url(raw_url)
            processed.append({
                "title": article.get("title", "No Title"),
                "desc": (article.get("description", "") or "")[:150] + "...",
                "source": article.get("source", {}).get("name", "Unknown"),
                "url": clean_link,
                "published": article.get("publishedAt", "")[:10]
            })
    return processed

def fetch_local_news() -> list:
    news_list = []
    try:
        googlenews = GoogleNews(lang='id', region='ID')
        googlenews.search("IHSG Saham Bursa Efek Indonesia Emiten")
        results = googlenews.result()
        for item in results[:4]: 
            raw_link = item.get('link', '#')
            # call 
            clean_link = clean_news_url(raw_link)
            news_list.append({
                'title': item.get('title', ''),
                'desc': item.get('desc', ''), 
                'source': item.get('media', 'Google News'),
                'published': item.get('date', 'Hari ini'),
                'url': clean_link
            })
        googlenews.clear()
    except Exception as e:
        print(f"Model Error (Local News): {e}")
    return news_list

def fetch_weekly_movers() -> list:
    candidates = [
        "NVDA", "TSLA", "AAPL", "MSFT", "COIN",
        "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK",
        "ADRO.JK", "UNTR.JK", "PTBA.JK", "PGAS.JK", "AKRA.JK",
        "ANTM.JK", "MDKA.JK", "INCO.JK", "TINS.JK",
        "GOTO.JK", "TLKM.JK", "ISAT.JK", "EXCL.JK",
        "ASII.JK", "ICBP.JK", "UNVR.JK", "AMRT.JK"
    ]
    try:
        batch_data = get_batch_stock_data(candidates, period="1mo")
    except Exception:
        return []
    trending_scores = []
    if not batch_data.empty:
        for ticker in candidates:
            try:
                stock_data = pd.DataFrame()
                if isinstance(batch_data.columns, pd.MultiIndex):
                    if ticker in batch_data.columns.levels[0]:
                        stock_data = batch_data[ticker].copy()
                else:
                    stock_data = batch_data.copy()
                if not stock_data.empty and len(stock_data) >= 7:
                    latest = stock_data["Close"].dropna().iloc[-1]
                    prev_week = stock_data["Close"].dropna().iloc[-7]
                    if prev_week > 0:
                        delta = ((latest - prev_week) / prev_week) * 100
                        trending_scores.append((ticker, float(delta), stock_data))
            except Exception:
                continue
    top_trending = sorted(trending_scores, key=lambda x: x[1], reverse=True)[:4]
    return top_trending