import streamlit as st
import time
from typing import Any

# MVC Modules
import modules.chatbot_model as model
import modules.chatbot_view as view

# Core Logic
from modules.chatbot_model import initialize_chat_session
from modules.auth_manager import check_quota_available, increment_usage

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

def show_chatbot() -> None:
    # 1. Auth Check
    current_user = st.session_state.get("username")
    if not st.session_state.get("logged_in") or not current_user:
        view.render_access_denied()
        return

    # 2. UI Setup
    view.render_sidebar_controls()
    view.render_header()

    # 3. Quota Check
    is_allowed, status_msg = check_quota_available(current_user)
    if is_allowed:
        view.render_account_status(status_msg)
    else:
        view.render_quota_error(status_msg)

    # 4. History Management
    if st.session_state.get("_chat_loaded_user") != current_user:
        st.session_state.messages = model.load_history(current_user)
        st.session_state["_chat_loaded_user"] = current_user
        # Reset session chat jika ganti user
        if "chat_session" in st.session_state: 
            del st.session_state.chat_session

    # 5. Gemini Init (USE AUTOMATIC FUNCTION CALLING DARI MODEL)
    try:
        if "chat_session" not in st.session_state:
            # initialize_chat_session sudah meng-inject tools dan set auto_function_calling=True
            st.session_state.chat_session = initialize_chat_session()
            
    except Exception as e:
        st.error(f"Service Unavailable: {e}")
        return

    # 6. Render History
    view.render_chat_messages(st.session_state.messages)

    # 7. Main Interaction Loop
    if is_allowed:
        if prompt := view.get_user_input():
            # Quota Double Check
            ok, _ = check_quota_available(current_user)
            if not ok: st.error("Quota Limit Reached."); st.stop()

            # SMART CONTEXT INJECTION
            keywords = ["portofolio", "portfolio", "holding", "saham saya", "investasi saya", "cek aset"]
            final_prompt_to_ai = prompt
            
            # Jika user tanya portfolio, inject datanya
            if any(k in prompt.lower() for k in keywords):
                with st.spinner("🔄 Mengambil data portofolio real-time..."):
                    context_data = model.get_portfolio_context(current_user)
                    # bungkus prompt user dengan data portfolio
                    final_prompt_to_ai = (
                        f"Context Data:\n{context_data}\n\n"
                        f"User Query: {prompt}\n"
                        f"Instruction: Jawab User Query berdasarkan Context Data di atas."
                    )
            
            # Save User Message to UI & History
            st.session_state.messages.append({"role": ROLE_USER, "content": prompt})
            with st.chat_message(ROLE_USER):
                st.markdown(prompt)
            model.save_history(current_user, st.session_state.messages)

            # Process Response
            process_ai_response_auto(current_user, final_prompt_to_ai)

def process_ai_response_auto(user: str, prompt_text: str):
    """
    Menangani respons menggunakan Automatic Function Calling SDK.
    Tidak ada handling manual loop di sini. Biarkan SDK bekerja.
    """
    try:
        with st.chat_message(ROLE_ASSISTANT):
            message_placeholder = st.empty()
            message_placeholder.markdown("*Sedang menganalisis pasar & menjalankan tools...*")
            
            # CLEAR CHART BUFFER SEBELUM EKSEKUSI
            if "last_chart" in st.session_state:
                st.session_state["last_chart"] = None

            # --- KIRIM KE GEMINI (AUTO EXECUTE)
            response = st.session_state.chat_session.send_message(prompt_text)
            
            # Ambil Text Final
            final_text = response.text
            message_placeholder.markdown(final_text)

            # --- CEK SIDE EFFECT: CHART
            chart_obj = None
            if st.session_state.get("last_chart") is not None:
                chart_obj = st.session_state["last_chart"]
                # Render Chart di UI
                st.plotly_chart(chart_obj, use_container_width=True)
                # Reset
                st.session_state["last_chart"] = None

            # SIMPAN KE HISTORY
            st.session_state.messages.append({
                "role": ROLE_ASSISTANT, 
                "content": final_text, 
                "chart": chart_obj
            })
            model.save_history(user, st.session_state.messages)
            
            increment_usage(user)

    except Exception as e:
        error_msg = str(e)
        if "index" in error_msg or "finish_reason" in error_msg:
            st.error("Maaf, permintaan terlalu kompleks atau data saham tidak ditemukan. Coba kode saham yang valid.")
        else:
            st.error(f"Terjadi kesalahan sistem: {error_msg}")