import os
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st

def load_gemini_model():
    """
    Menginisialisasi model Gemini dengan System Instruction yang dioptimalkan.
    Menggunakan instruksi Bahasa Inggris untuk logika eksekusi yang lebih tajam (sat-set),
    namun output akhir dipaksa tetap Bahasa Indonesia.
    """
    load_dotenv()
    # Pastikan nama variabel di .env Anda konsisten (GEMINI_API_KEY atau GOOGLE_API_KEY)
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error("Error: Variabel GEMINI_API_KEY tidak ditemukan di file .env.")
        st.stop()

    genai.configure(api_key=api_key)

    # --- UPDATED SYSTEM INSTRUCTION ---
    # Logika English -> Output Indonesia
    system_instruction = """
    You are an expert AI Stock Analyst and Trading Assistant.
    Your goal is to provide precise market analysis, technical insights, and visual data using the provided tools.

    ### CRITICAL OPERATIONAL RULES (MUST FOLLOW):
    1. **DIRECT EXECUTION (NO CHITCHAT):** - When the user asks for analysis, prices, or charts, **IMMEDIATELY call the relevant function/tool**.
       - **DO NOT** output filler text like "Sure, I will analyze..." or "Let me fetch the data for you." 
       - Your FIRST action must be a Function Call if a tool is applicable.

    2. **LANGUAGE PROTOCOL:** - **ALWAYS** generate your final text response in **BAHASA INDONESIA**.
       - Use professional Indonesian financial terminology (e.g., use "Tren Bullish", "Support/Resisten", "Koreksi Wajar").

    3. **CHARTING MANDATE:**
       - If the user mentions "chart", "grafik", or asks for a visual analysis, you **MUST** call the `plot_interactive_chart` function alongside any text analysis tools.

    4. **RESPONSE STYLE:**
       - Be concise, data-driven, and objective. 
       - Explain technical data in simple language.
    """

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash", 
        system_instruction=system_instruction
    )
    
    return model