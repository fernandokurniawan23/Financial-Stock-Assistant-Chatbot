import streamlit as st
from modules.ui_assets import ICONS

"""
MAIN VIEW MODULE
----------------
Responsibility: Rendering the App Shell (Login & Sidebar).
Handles the visual presentation of authentication forms and navigation menus.
"""

def render_login_page() -> dict:
    """
    Renders the centered login/registration card.
    Returns a dictionary containing the user action (login/register) and credentials.
    """
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown(f"""
            <div style="text-align:center; margin-bottom:30px;">
                <h1 style="color:#e6edf3; font-size:32px; margin-bottom:10px;">FinAssist Portal</h1>
                <p style="color:#8b949e;">Secure Access to Financial Intelligence</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Tabs for better UX
        tab_login, tab_register = st.tabs(["Login Access", "Create Account"])
        
        result = {"action": None, "username": "", "password": ""}
        
        with tab_login:
            st.markdown(f"<div style='text-align:center; margin:20px 0;'>{ICONS['key']}</div>", unsafe_allow_html=True)
            with st.form("login_form"):
                u = st.text_input("Username").strip()
                p = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Authenticate", use_container_width=True, type="primary")
                
                if submitted:
                    result = {"action": "login", "username": u, "password": p}

        with tab_register:
            with st.form("register_form"):
                u = st.text_input("Choose Username").strip()
                p = st.text_input("Choose Password", type="password")
                submitted = st.form_submit_button("Register Account", use_container_width=True)
                
                if submitted:
                    result = {"action": "register", "username": u, "password": p}
                    
        return result

def render_sidebar(username: str, tier: str) -> str:
    """
    Renders the navigation sidebar with user profile and tier info.
    Returns the selected page name based on button clicks.
    """
    selected_page = None
    
    with st.sidebar:
        # Profile Section
        st.markdown(f"""
            <div style="text-align:center; padding: 20px 0;">
                {ICONS['user_circle']}
                <h3 style="margin:10px 0 0 0; color:#e6edf3;">{username}</h3>
                <p style="margin:0; font-size:12px; color:#8b949e;">Active Session</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Tier Badge
        tier_color = "#2ea043" if tier == "pro" else "#8b949e"
        tier_icon = ICONS['star_filled'] if tier == "pro" else ICONS['user']
        border_style = f"1px solid {tier_color}"
        
        st.markdown(f"""
            <div style="
                display:flex; align-items:center; justify-content:center; gap:8px;
                background:rgba(255,255,255,0.05); padding:8px; border-radius:6px;
                border: {border_style}; margin-bottom: 30px;">
                {tier_icon}
                <span style="color:{tier_color}; font-weight:bold; letter-spacing:1px;">{tier.upper()} PLAN</span>
            </div>
        """, unsafe_allow_html=True)

        # Upgrade CTA (If Free)
        if tier == "free":
            st.info("Unlock advanced AI features.")
            if st.button("Upgrade to PRO (Demo)", use_container_width=True):
                return "UPGRADE_ACTION"
        
        st.divider()
        
        # Navigation Menu
        # Note: We use standard Streamlit buttons for navigation to ensure stability.
        # Custom HTML buttons in sidebar are tricky with Streamlit's event loop.
        st.markdown("### Navigation")
        
        if st.button("Dashboard", use_container_width=True):
            selected_page = "Dashboard"
            
        if st.button("AI Chatbot", use_container_width=True):
            selected_page = "Chatbot"
            
        if st.button("My Assets", use_container_width=True):
            selected_page = "Watchlist"
            
        st.divider()
        
        # Logout
        if st.button("Sign Out", use_container_width=True, type="secondary"):
            return "LOGOUT_ACTION"
            
    return selected_page