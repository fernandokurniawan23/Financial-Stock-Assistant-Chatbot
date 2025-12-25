import streamlit as st
import modules.dashboard_model as model
import modules.dashboard_view as view

"""
DASHBOARD CONTROLLER
--------------------
Responsibility: Orchestration Only.
Fetch Data (Model) -> Render UI (View).
"""

def show_dashboard():
    # 1. Initialize Styles
    view.render_global_styles()
    
    # 2. Data Fetching (Model)
    with st.spinner("Analyzing Market Data..."):
        status = model.get_system_status()
        ticker_data = model.fetch_ticker_tape_data()
        global_news = model.fetch_global_news()
        local_news = model.fetch_local_news()
        weekly_movers = model.fetch_weekly_movers()

    # 3. Render Layout
    
    # A. HERO HEADER
    view.render_hero_header()
    
    # B. Ticker Tape
    view.render_ticker_bar(ticker_data, status)
    
    # C. Global News
    view.render_news_section(global_news)
    
    # D. Local News
    view.render_local_news_section(local_news)

    # E. Weekly Movers
    view.render_weekly_movers(weekly_movers)

    # F. Footer
    view.render_footer()