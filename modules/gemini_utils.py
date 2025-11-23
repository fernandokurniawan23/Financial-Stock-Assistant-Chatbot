import os
from dotenv import load_dotenv
from google import generativeai as genai
import streamlit as st

def load_gemini_model():
    """Inisialisasi Gemini model dari .env"""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error("❌ Gagal: Variabel GEMINI_API_KEY tidak ditemukan di file .env.")
        st.stop()

    genai.configure(api_key=api_key)
    system_instruction = """
    Anda adalah asisten analisis saham yang ahli, ramah, dan membantu.
    Gunakan hanya fungsi yang telah disediakan untuk Anda.
    Jangan tampilkan data mentah — jelaskan dalam bahasa yang mudah dipahami.
    """

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_instruction
    )
    return model
