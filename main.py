import streamlit as st
from dotenv import load_dotenv

# Import Views
import modules.main_view as main_view
from modules.ui_assets import DASHBOARD_CSS

# Import Controllers (Page Logic)
from dashboard import show_dashboard
from chatbot import show_chatbot
from watchlist import show_watchlist

# Import Business Logic
from modules.auth_manager import verify_login, register_user, get_user_tier, upgrade_to_pro

# 1. App Configuration
load_dotenv()
st.set_page_config(
    page_title="FinAssist", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Inject Global CSS
st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
# Hide default Streamlit Nav
st.markdown("""<style>[data-testid="stSidebarNav"] { display: none !important; }</style>""", unsafe_allow_html=True)

# 2. State Management
if "active_page" not in st.session_state: st.session_state.active_page = "Dashboard"
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""

def logout():
    """Clears session and resets state."""
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.active_page = "Dashboard"
    st.rerun()

# 3. Main Application Flow
if not st.session_state.logged_in:
    # --- RENDER LOGIN VIEW ---
    cred_data = main_view.render_login_page()
    
    if cred_data["action"] == "login":
        if verify_login(cred_data["username"], cred_data["password"]):
            st.session_state.logged_in = True
            st.session_state.username = cred_data["username"]
            st.rerun()
        else:
            st.error("Authentication failed. Invalid username or password.")
            
    elif cred_data["action"] == "register":
        ok, msg = register_user(cred_data["username"], cred_data["password"])
        if ok: st.success("Registration successful! Please login.")
        else: st.error(f"Registration failed: {msg}")

else:
    # --- AUTHENTICATED SESSION ---
    
    # A. Fetch Data
    current_tier = get_user_tier(st.session_state.username)
    
    # B. Render Sidebar & Handle Navigation
    nav_action = main_view.render_sidebar(st.session_state.username, current_tier)
    
    if nav_action == "LOGOUT_ACTION":
        logout()
    elif nav_action == "UPGRADE_ACTION":
        upgrade_to_pro(st.session_state.username)
        st.toast("Account upgraded to PRO successfully!", icon="🚀")
        st.rerun()
    elif nav_action:
        st.session_state.active_page = nav_action
        st.rerun()

    # C. Router - Load Page Controller 
    if st.session_state.active_page == "Dashboard":
        show_dashboard()
    elif st.session_state.active_page == "Chatbot":
        show_chatbot()
    elif st.session_state.active_page == "Watchlist":
        show_watchlist()