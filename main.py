import streamlit as st
import os
from dotenv import load_dotenv
from pages.dashboard import show_dashboard
from pages.chatbot import show_chatbot
from pages.watchlist import show_watchlist

load_dotenv()

st.set_page_config(
    page_title="FinAssist", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# Inisialisasi state halaman aktif
if "active_page" not in st.session_state:
    st.session_state.active_page = "Dashboard"

# =========================================
# 🧭 Sidebar Navigasi
# =========================================
with st.sidebar:
    st.title("🧭 Navigasi")
    st.write("Pilih halaman:")
    
    if st.button("🏠 Dashboard", use_container_width=True):
        st.session_state.active_page = "Dashboard"
        st.rerun()
        
    if st.button("💬 Chatbot AI", use_container_width=True):
        st.session_state.active_page = "Chatbot"
        st.rerun()
        
    if st.button("📋 Watchlist & Portofolio", use_container_width=True):
        st.session_state.active_page = "Watchlist"
        st.rerun()
        
    st.divider()
    st.caption("FinAssist v1.0")

# =========================================
# 🔀 Routing Halaman
# =========================================
if st.session_state.active_page == "Dashboard":
    show_dashboard()
elif st.session_state.active_page == "Chatbot":
    show_chatbot()
elif st.session_state.active_page == "Watchlist":
    show_watchlist()