import streamlit as st
import pandas as pd

# MVC Imports
import modules.watchlist_model as model
import modules.watchlist_view as view
from modules.stock_tools import get_batch_stock_data
from modules.ui_assets import ICONS

"""
WATCHLIST CONTROLLER
--------------------
Responsibility: Application Flow, State Management, and Event Handling.
Connects the Model (Data) with the View (UI).
"""

def show_watchlist() -> None:
    """
    Main Entry Point for Watchlist & Portfolio Module.
    """
    # 1. Authentication Check
    current_user = st.session_state.get("username")
    if not current_user:
        st.warning("🔒 Access Denied. Please login via Dashboard.")
        return

    # 2. State Initialization (Load Data)
    if "user_data" not in st.session_state or st.session_state.get("_current_loaded_user") != current_user:
        st.session_state.user_data = model.load_user_data(current_user)
        st.session_state["_current_loaded_user"] = current_user

    # 3. Render Header
    view.render_header(current_user)
    
    # 4. Render Tabs
    # We use HTML/SVG icons in tab names for visual consistency
    tab1, tab2 = st.tabs(["👀 Watchlist", "💰 Portfolio"])
    
    # ==========================
    # TAB 1: WATCHLIST LOGIC
    # ==========================
    with tab1:
        # A. Add Stock Logic
        new_ticker = view.render_add_watchlist_form()
        if new_ticker:
            if new_ticker not in st.session_state.user_data["watchlist"]:
                st.session_state.user_data["watchlist"].append(new_ticker)
                model.save_user_data(current_user, st.session_state.user_data)
                st.rerun()
            else:
                st.toast("Stock already in watchlist", icon="⚠️")

        # B. Display Stocks
        watchlist = st.session_state.user_data["watchlist"]
        if watchlist:
            # Batch fetch for performance
            batch_data = get_batch_stock_data(watchlist, period="1mo")
            
            # Grid Layout
            cols = st.columns(3)
            for i, ticker in enumerate(watchlist):
                with cols[i % 3]:
                    # Extract specific df for this ticker
                    data = pd.DataFrame()
                    try:
                        if not batch_data.empty:
                            if isinstance(batch_data.columns, pd.MultiIndex) and ticker in batch_data.columns.levels[0]:
                                data = batch_data[ticker].copy()
                            elif len(watchlist) == 1 and "Close" in batch_data.columns:
                                data = batch_data.copy()
                    except Exception:
                        pass
                    
                    # Define Delete Handler
                    def delete_handler(t_symbol):
                        st.session_state.user_data["watchlist"].remove(t_symbol)
                        model.save_user_data(current_user, st.session_state.user_data)
                        st.rerun()

                    # Render
                    view.render_stock_card(ticker, data, i, delete_handler)
        else:
            st.info("Watchlist is empty. Add a stock to start tracking!")

    # ==========================
    # TAB 2: PORTFOLIO LOGIC
    # ==========================
    with tab2:
        # A. Add Transaction Logic
        form_data = view.render_portfolio_form()
        if form_data["submitted"]:
            if form_data["symbol"] and form_data["price"] > 0 and form_data["qty"] > 0:
                st.session_state.user_data["portfolio"].append({
                    "symbol": form_data["symbol"], 
                    "buy_price": form_data["price"], 
                    "quantity": form_data["qty"], 
                    "currency": form_data["currency"]
                })
                model.save_user_data(current_user, st.session_state.user_data)
                st.success("Transaction saved successfully!")
                st.rerun()
            else:
                st.error("Please fill in all fields correctly.")

        # B. Calculate & Render
        portfolio = st.session_state.user_data["portfolio"]
        if portfolio:
            # Calculation moved to Model
            calc_result = model.calculate_portfolio_performance(portfolio)
            
            # Render Summary
            view.render_portfolio_summary(calc_result["summary"])
            
            # Define Delete Handler
            def delete_pf_handler(idx):
                st.session_state.user_data["portfolio"].pop(idx)
                model.save_user_data(current_user, st.session_state.user_data)
                st.rerun()

            # Render Table
            view.render_portfolio_table(calc_result["items"], delete_pf_handler)
        else:
            st.info("Portfolio is empty. Record your first investment above.")