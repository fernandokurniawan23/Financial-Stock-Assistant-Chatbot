import os
import streamlit as st
from newsapi import NewsApiClient

@st.cache_data(ttl=1800)
def get_latest_news():
    """
    Mengambil 50 berita bisnis teratas dari AS.
    Menggunakan cache agar tidak cepat menghabiskan kuota NewsAPI.
    """
    api_key = os.getenv("NEWS_API_KEY")

    if not api_key:
        return {"articles": []}

    try:
        newsapi = NewsApiClient(api_key=api_key)
        
        # Ambil 50 berita
        response = newsapi.get_top_headlines(
            category="business",
            language="en",
            country="us", 
            page_size=100 
        )
        
        if response.get('status') == 'ok':
            return response
        else:
            return {"articles": []}
            
    except Exception as e:
        return {"articles": []}