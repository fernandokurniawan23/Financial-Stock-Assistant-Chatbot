import yfinance as yf
import streamlit as st
import pandas as pd
import time
import requests

# Ambil data 1 saham (detail)
@st.cache_data(ttl=600, show_spinner=False)
def get_stock_data_safe(ticker: str, period: str = "1mo") -> pd.DataFrame:
    try:
        time.sleep(0.1)
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if _is_valid(data):
             return _flatten_columns(data)
    except Exception:
        pass
    return pd.DataFrame()

# Ambil data banyak saham sekaligus
@st.cache_data(ttl=900, show_spinner=False)
def get_batch_stock_data(tickers: list, period: str = "1mo") -> pd.DataFrame:
    """
    Mengambil data banyak saham dalam SATU kali request.
    Sangat efisien untuk menghindari rate limit.
    """
    if not tickers:
        return pd.DataFrame()
    
    try:
        ticker_str = " ".join(tickers)
        # group_by='ticker'
        data = yf.download(ticker_str, period=period, group_by='ticker', progress=False, auto_adjust=True)
        return data
    except Exception as e:
        print(f"Batch download error: {e}")
        return pd.DataFrame()

#  Helper Functions
def _is_valid(df: pd.DataFrame) -> bool:
    return not df.empty and len(df) > 0

def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.get_level_values(0)
        except:
            pass 
    return df

# Cek status Yahoo API
def yahoo_status() -> str:
    try:
        res = requests.get("https://finance.yahoo.com", timeout=3)
        if res.status_code == 200: return "🟢 Online"
        elif res.status_code == 429: return "🟡 Rate Limited"
        else: return f"🔴 Gangguan ({res.status_code})"
    except:
        return "🔴Offline"