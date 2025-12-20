import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from modules.ui_assets import ICONS

"""
WATCHLIST VIEW MODULE
---------------------
Responsibility: Rendering UI Components.
Displays the Watchlist grid, Stock Cards, Portfolio Table, and Forms.
Strictly visual - no business logic or data fetching.
"""

def render_header(username: str):
    """Renders the main module header."""
    st.markdown("<h1>📋 My Assets</h1>", unsafe_allow_html=True)
    st.caption(f"Managing portfolio for account: **{username}**")

def render_add_watchlist_form() -> str:
    """Renders the form to add a new stock to watchlist."""
    with st.form("add_watchlist"):
        c1, c2 = st.columns([3, 1])
        new_ticker = c1.text_input("Add Ticker:", placeholder="AAPL, BBCA.JK").upper().strip()
        
        # Using HTML in button requires custom component or just text, using standard button with icon logic
        submitted = c2.form_submit_button("Add", use_container_width=True)
        return new_ticker if submitted else None

def render_stock_card(ticker: str, data: pd.DataFrame, index: int, delete_callback):
    """
    Renders a single stock card with price, change, and sparkline chart.
    """
    if data.empty or "Close" not in data.columns or len(data) < 2:
        st.warning(f"{ticker}: Data Unavailable")
        if st.button(f"Remove", key=f"del_{ticker}_{index}"):
            delete_callback(ticker)
        return

    # Data extraction
    last_price = data["Close"].iloc[-1]
    start_price = data["Close"].iloc[0]
    price_change = last_price - start_price
    pct_change = (price_change / start_price) * 100 if start_price != 0 else 0
    
    currency_symbol = "Rp" if ".JK" in ticker else "$"
    color = "#2ea043" if price_change >= 0 else "#da3633"
    icon = ICONS["trending_up"] if price_change >= 0 else ICONS["trending_down"]
    fmt_price = f"{last_price:,.0f}" if currency_symbol == "Rp" else f"{last_price:,.2f}"

    # HTML Rendering
    st.markdown(f"""
    <div class="stock-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="color:#facc15; margin:0; font-size:18px;">{ticker}</h3>
            <span style="font-size:16px; font-weight:bold; color:#e6edf3;">{currency_symbol} {fmt_price}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
            <span style="color:{color}; font-weight:600; display:flex; align-items:center; gap:4px;">
                {icon} {pct_change:+.2f}%
            </span>
            <span style="color:#8b949e; font-size:11px;">30 Days</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sparkline Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, y=data["Close"], 
        mode='lines', 
        line=dict(color=color, width=2), 
        fill='tozeroy', 
        fillcolor=f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.1)"
    ))
    fig.update_layout(
        height=40, margin=dict(l=0,r=0,t=0,b=0), 
        xaxis=dict(visible=False), yaxis=dict(visible=False), 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

    # Delete Button (Standard Streamlit due to event handling limitations)
    col_del, _ = st.columns([1, 3])
    with col_del:
        if st.button("Trash", key=f"del_btn_{ticker}_{index}"):
            delete_callback(ticker)

def render_portfolio_form() -> dict:
    """Renders the Add Transaction form."""
    input_data = {}
    with st.expander("💼 Record New Transaction", expanded=False):
        with st.form("add_portfolio"):
            c1, c2 = st.columns(2)
            input_data["symbol"] = c1.text_input("Ticker Symbol", placeholder="BBCA.JK / NVDA").upper().strip()
            curr_raw = c2.selectbox("Currency", ["IDR (Rupiah)", "USD (Dollar)"])
            input_data["currency"] = "IDR" if "IDR" in curr_raw else "USD"
            
            c3, c4 = st.columns(2)
            input_data["price"] = c3.number_input("Buy Price", min_value=0.0, step=0.01, format="%.2f")
            input_data["qty"] = c4.number_input("Quantity", min_value=1, step=1)

            input_data["submitted"] = st.form_submit_button("Save Transaction", use_container_width=True)
    return input_data

def render_portfolio_summary(summary_data: dict):
    """Renders the Metric Cards for Portfolio Summary."""
    st.markdown("### 📊 Performance Summary")
    
    # IDR
    idr_data = summary_data.get("IDR", {})
    if idr_data.get("invested", 0) > 0:
        inv = idr_data["invested"]
        val = idr_data["value"]
        pl = val - inv
        pl_pct = (pl / inv) * 100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Invested (IDR)", f"Rp {inv:,.0f}")
        c2.metric("Asset Value (IDR)", f"Rp {val:,.0f}", delta=f"{pl:,.0f}")
        c3.metric("Return (IDR)", f"{pl_pct:+.2f}%")
        st.divider()

    # USD
    usd_data = summary_data.get("USD", {})
    if usd_data.get("invested", 0) > 0:
        inv = usd_data["invested"]
        val = usd_data["value"]
        pl = val - inv
        pl_pct = (pl / inv) * 100
        
        d1, d2, d3 = st.columns(3)
        d1.metric("Total Invested (USD)", f"${inv:,.2f}")
        d2.metric("Asset Value (USD)", f"${val:,.2f}", delta=f"{pl:,.2f}")
        d3.metric("Return (USD)", f"{pl_pct:+.2f}%")

def render_portfolio_table(items: list, delete_callback):
    """Renders the detailed portfolio table."""
    st.markdown("### 📜 Asset Details")
    
    # Table Header
    h1, h2, h3, h4, h5 = st.columns([1.5, 1.5, 1.2, 2, 0.8])
    h1.markdown("**Asset**")
    h2.markdown("**Price**")
    h3.markdown("**Qty**")
    h4.markdown("**P/L**")
    h5.markdown("**Action**")
    st.markdown("<hr style='margin: 5px 0; border-color: #30363d'>", unsafe_allow_html=True)

    for item in items:
        fmt = "Rp {:,.0f}" if item['currency'] == "IDR" else "$ {:,.2f}"
        color = "#2ea043" if item['gain_loss'] >= 0 else "#da3633"
        if item['is_error']: color = "#eab308" # Yellow warning
        
        r1, r2, r3, r4, r5 = st.columns([1.5, 1.5, 1.2, 2, 0.8])
        
        # Asset Info
        r1.markdown(f"**{item['symbol']}**<br><span style='font-size:12px; color:#8b949e'>Buy: {fmt.format(item['buy_price'])}</span>", unsafe_allow_html=True)
        
        # Current Price
        err_icon = ICONS['alert'] if item['is_error'] else "" # Make sure alert icon exists or remove
        price_display = f"{fmt.format(item['curr_price'])}"
        if item['is_error']:
             price_display += " ⚠️"
        r2.markdown(price_display)
        
        # Qty
        r3.markdown(f"{item['qty']}")
        
        # Profit/Loss
        pl_txt = f"{fmt.format(item['gain_loss'])} ({item['gain_pct']:+.2f}%)"
        r4.markdown(f"<span style='color:{color}; font-weight:bold'>{pl_txt}</span>", unsafe_allow_html=True)
        
        # Delete Action
        if r5.button("x", key=f"del_pf_{item['index']}", help="Delete Entry"):
            delete_callback(item['index'])
        
        st.markdown("<div class='section-divider' style='margin: 5px 0'></div>", unsafe_allow_html=True)