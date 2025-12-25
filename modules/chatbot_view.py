import streamlit as st
import time
from modules.ui_assets import ICONS

"""
CHATBOT VIEW MODULE
-------------------
Responsibility: UI Rendering and User Interaction.
Handles visual components and user input capture.
"""

def render_header():
    """Renders the main Chatbot header."""
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom: 20px;">
            <div style="background:#161b22; padding:10px; border-radius:10px; border:1px solid #30363d;">
                {ICONS['bot']}
            </div>
            <div>
                <h1 style="margin:0; font-size:24px; color:#e6edf3;">Stock Analysis Pro</h1>
                <p style="margin:0; font-size:14px; color:#8b949e;">AI-Powered Financial Assistant</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_access_denied():
    """Renders the access denied warning."""
    st.markdown(f"""
        <div style="background:#2b1d1d; border:1px solid #da3633; padding:20px; border-radius:8px; display:flex; gap:15px; align-items:center;">
            <div style="color:#da3633;">{ICONS['lock']}</div>
            <div>
                <h3 style="margin:0 0 5px 0; color:#da3633;">Access Denied</h3>
                <p style="margin:0; color:#e6edf3; font-size:14px;">Please authenticate via the Dashboard to access the Pro Assistant.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_quota_error(msg: str):
    """Renders quota limit errors."""
    st.markdown(f"""
        <div style="background:#2b1d1d; border:1px solid #da3633; padding:15px; border-radius:8px; margin-bottom:20px; display:flex; gap:10px; align-items:center;">
            <div style="color:#da3633;">{ICONS['alert']}</div>
            <span style="color:#e6edf3;">{msg}</span>
        </div>
    """, unsafe_allow_html=True)

def render_account_status(status_msg: str):
    """Renders a subtle status bar for account quota."""
    st.markdown(f"""
        <div style="font-size:12px; color:#8b949e; margin-bottom:20px; border-bottom:1px solid #30363d; padding-bottom:10px;">
            Account Status: <span style="color:#58a6ff;">{status_msg}</span>
        </div>
    """, unsafe_allow_html=True)

def render_sidebar_controls():
    """
    Renders sidebar interface for chat session management.
    Handles history reset functionality.
    """
    with st.sidebar:
        st.markdown("### Session Management")
        
        if st.button("Reset Chat", use_container_width=True):
            # Clear session state
            if "chat_history" in st.session_state:
                st.session_state.chat_history = []
            if "messages" in st.session_state:
                st.session_state.messages = []
            
            st.toast("Conversation history purged.", icon="🧹")
            time.sleep(0.5)
            st.rerun()

def render_chat_messages(messages: list):
    """
    Iterates through the message history and renders them.
    Handles distinct styling for User vs Assistant.
    """
    for msg in messages:
        role = msg["role"]
        
        with st.chat_message(role):
            st.markdown(msg["content"])
            
            # Check for Charts
            if msg.get("chart"):
                st.plotly_chart(msg["chart"], use_container_width=True)

def get_user_input() -> str:
    """Wrapper for the chat input field."""
    return st.chat_input("Ask about stocks, portfolio, or market trends...")