import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from modules.ui_assets import ICONS, DASHBOARD_CSS

"""
WATCHLIST VIEW MODULE
---------------------
Responsibility: Rendering UI Components.
Uses Centralized UI Assets (CSS & SVG) for consistent design.
"""

def render_section_header(title: str, icon_key: str):
    """Renders a clean section header with SVG icon from Assets."""
    icon = ICONS.get(icon_key, ICONS['activity']) # Fallback to activity if missing
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom: 10px; border-bottom: 1px solid #30363d; padding-bottom: 5px;">
        {icon}
        <h3 style="margin:0; font-size: 18px; color: #e6edf3;">{title}</h3>
    </div>
    """, unsafe_allow_html=True)

def render_header(username: str):
    """
    Renders the main module header and INJECTS CSS.
    """
    # 1. Inject Global CSS
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
    
    # 2. Render Header Content
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom: 20px;">
        {ICONS['dashboard']}
        <div>
            <h1 style="margin:0; font-size: 28px;">My Assets</h1>
            <span style="font-size: 14px; color: #8b949e;">Portfolio Manager for: <strong>{username}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_add_watchlist_form() -> str:
    """Renders the form to add a new stock to watchlist."""
    with st.form("add_watchlist"):
        c1, c2 = st.columns([3, 1])
        new_ticker = c1.text_input("Add Ticker:", placeholder="AAPL, BBCA.JK", label_visibility="collapsed").upper().strip()
        
        # Button add
        submitted = c2.form_submit_button("Add Ticker", use_container_width=True)
        return new_ticker if submitted else None

def render_stock_card(ticker: str, data: pd.DataFrame, index: int, delete_callback):
    """
    Renders a single stock card using styles defined in ui_assets.py.
    """
    if data.empty or "Close" not in data.columns or len(data) < 2:
        st.warning(f"{ticker}: Data Unavailable")
        if st.button(f"Delete", key=f"del_{ticker}_{index}"):
            delete_callback(ticker)
        return

    # Data extraction
    last_price = data["Close"].iloc[-1]
    start_price = data["Close"].iloc[0]
    price_change = last_price - start_price
    pct_change = (price_change / start_price) * 100 if start_price != 0 else 0
    
    currency_symbol = "Rp" if ".JK" in ticker else "$"
    
    # Warna & Ikon berdasarkan Tren
    if price_change >= 0:
        color = "#2ea043"
        icon_svg = ICONS["trending_up"]
    else:
        color = "#da3633"
        icon_svg = ICONS["trending_down"]
    
    fmt_price = f"{last_price:,.0f}" if currency_symbol == "Rp" else f"{last_price:,.2f}"

    # HTML Rendering
    st.markdown(f"""
    <div class="stock-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="color:#facc15; margin:0; font-size:16px; font-family:sans-serif;">{ticker}</h3>
            <span style="font-size:16px; font-weight:bold; color:#e6edf3;">{currency_symbol} {fmt_price}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
            <span style="color:{color}; font-weight:600; font-size: 14px; display:flex; align-items:center; gap:4px;">
                {icon_svg} {pct_change:+.2f}%
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
        height=35, margin=dict(l=0,r=0,t=0,b=0), 
        xaxis=dict(visible=False), yaxis=dict(visible=False), 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

    # Delete Button
    col_del, _ = st.columns([1, 3])
    with col_del:
        if st.button("Remove", key=f"del_btn_{ticker}_{index}"):
            delete_callback(ticker)

def render_portfolio_form() -> dict:
    """Renders the Add Transaction form."""
    input_data = {}
    
    # Container with Expander
    with st.expander("Record New Transaction", expanded=False):
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
    render_section_header("Performance Summary", "bar_chart")
    
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
        st.markdown("<div style='margin-bottom: 15px'></div>", unsafe_allow_html=True)

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
    render_section_header("Asset Details", "list")
    
    # Custom Table Header
    st.markdown("""
    <div style="display: grid; grid-template-columns: 2fr 1.5fr 1fr 2fr 0.5fr; gap: 10px; color: #8b949e; font-size: 14px; margin-bottom: 8px;">
        <div>ASSET</div>
        <div>PRICE</div>
        <div>QTY</div>
        <div>P/L</div>
        <div style='text-align:center'>ACT</div>
    </div>
    <hr style='margin: 0 0 10px 0; border-color: #30363d'>
    """, unsafe_allow_html=True)

    for item in items:
        fmt = "Rp {:,.0f}" if item['currency'] == "IDR" else "$ {:,.2f}"
        color = "#2ea043" if item['gain_loss'] >= 0 else "#da3633"
        if item['is_error']: color = "#eab308"
        
        # Grid Layout
        r1, r2, r3, r4, r5 = st.columns([2, 1.5, 1, 2, 0.5])
        
        # Asset Info
        r1.markdown(f"<div style='font-weight:bold'>{item['symbol']}</div><div style='font-size:12px; color:#8b949e'>Avg: {fmt.format(item['buy_price'])}</div>", unsafe_allow_html=True)
        
        # Current Price & Error Handling
        price_display = f"{fmt.format(item['curr_price'])}"
        if item['is_error']:
             # Menggunakan ICONS['alert'] dari ui_assets
             price_display += f" <span style='vertical-align:middle; display:inline-block'>{ICONS['alert']}</span>"
        r2.markdown(f"<div style='padding-top:2px'>{price_display}</div>", unsafe_allow_html=True)
        
        # Qty
        r3.markdown(f"<div style='padding-top:2px'>{item['qty']}</div>", unsafe_allow_html=True)
        
        # Profit/Loss
        pl_txt = f"{fmt.format(item['gain_loss'])} ({item['gain_pct']:+.2f}%)"
        r4.markdown(f"<div style='color:{color}; font-weight:600; padding-top:2px'>{pl_txt}</div>", unsafe_allow_html=True)
        
        # Delete Action
        if r5.button("x", key=f"del_pf_{item['index']}", help="Delete Entry"):
            delete_callback(item['index'])
        
        st.markdown("<hr style='margin: 5px 0; border-color: #21262d'>", unsafe_allow_html=True)