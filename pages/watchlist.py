import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf 
from modules.stock_tools import get_batch_stock_data
import os, json, tempfile, shutil

# ==========================================
# CONFIGURATION & STYLING
# ==========================================

# Custom CSS for column alignment and row separation
st.markdown("""
<style>
div[data-testid="column"] {
    display: flex;
    align-items: center;
}
.stock-row {
    padding: 10px 0;
    border-bottom: 1px solid #30363d;
}
</style>
""", unsafe_allow_html=True)

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "user_data.json")

# ==========================================
# DATA PERSISTENCE LAYER
# ==========================================

def ensure_data_loaded() -> None:
    """Ensures user_data session state is initialized and loaded from disk."""
    if "user_data" not in st.session_state:
        st.session_state.user_data = {"watchlist": [], "portfolio": []}
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    st.session_state.user_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

def save_user_data() -> None:
    """Atomically saves the current session state to JSON file."""
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, dir=DATA_DIR) as tmp:
            json.dump(st.session_state.user_data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.move(tmp.name, DATA_FILE)
    except Exception as e:
        st.error(f"Failed to save data: {e}")

# ==========================================
# MAIN UI FUNCTION
# ==========================================

def show_watchlist() -> None:
    """
    Renders the Investment Dashboard containing Watchlist and Portfolio tabs.
    Handles asset CRUD operations, multi-currency display (IDR/USD), 
    and real-time performance tracking.
    """
    ensure_data_loaded()
    
    st.markdown("<h1>📋 Aset Saya</h1>", unsafe_allow_html=True)
    st.caption("Kelola daftar pantau dan portofolio investasi kamu di sini.")
    
    tab1, tab2 = st.tabs(["👀 Watchlist", "💰 Portofolio"])

    # ---------------------------------------------------------
    # TAB 1: WATCHLIST MANAGEMENT
    # ---------------------------------------------------------
    with tab1:
        col_add, _ = st.columns([2, 1])
        with col_add:
            with st.form("add_watchlist"):
                c1, c2 = st.columns([3, 1])
                new_ticker = c1.text_input("Tambah Saham:", placeholder="AAPL, BBCA.JK").upper().strip()
                if c2.form_submit_button("➕ Tambah", use_container_width=True):
                    if new_ticker and new_ticker not in st.session_state.user_data["watchlist"]:
                        st.session_state.user_data["watchlist"].append(new_ticker)
                        save_user_data()
                        st.rerun()

        watchlist = st.session_state.user_data["watchlist"]
        if watchlist:
            # Batch data retrieval optimization
            batch_data = get_batch_stock_data(watchlist, period="1mo")
            cols = st.columns(3)
            
            for i, ticker in enumerate(watchlist):
                with cols[i % 3]:
                    data = pd.DataFrame()
                    try:
                        if not batch_data.empty:
                            if isinstance(batch_data.columns, pd.MultiIndex) and ticker in batch_data.columns.levels[0]:
                                data = batch_data[ticker].copy()
                            elif len(watchlist) == 1 and "Close" in batch_data.columns:
                                data = batch_data.copy()
                    except Exception: 
                        pass

                    currency_symbol = "Rp" if ".JK" in ticker else "$"
                    
                    # Validate data integrity before rendering
                    if not data.empty and "Close" in data.columns and len(data) >= 2 and not pd.isna(data["Close"].iloc[-1]):
                        last_price = data["Close"].iloc[-1]
                        start_price = data["Close"].iloc[0]
                        price_change = last_price - start_price
                        pct_change = (price_change / start_price) * 100 if start_price != 0 else 0
                        
                        # UI Attributes
                        color = "#16a34a" if price_change >= 0 else "#dc2626"
                        icon = "▲" if price_change >= 0 else "▼"
                        fmt_price = f"{last_price:,.0f}" if currency_symbol == "Rp" else f"{last_price:,.2f}"

                        # Render Stock Card
                        st.markdown(f"""
                        <div class="stock-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h3 style="color:#facc15; margin:0;">{ticker}</h3>
                                <span style="font-size:18px; font-weight:bold;">{currency_symbol} {fmt_price}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                                <span style="color:{color}; font-weight:600;">{icon} {pct_change:+.2f}%</span>
                                <span style="color:#9da7b2; font-size:12px;">1 Bulan</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Sparkline Chart
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=data.index, y=data["Close"], mode='lines', line=dict(color=color, width=2), fill='tozeroy', fillcolor=f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.1)"))
                        fig.update_layout(height=50, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    else:
                        st.warning(f"{ticker}: Data Unavailable")

                    # Delete Action
                    if st.button(f"🗑️ Hapus", key=f"del_{ticker}"):
                         st.session_state.user_data["watchlist"].remove(ticker)
                         save_user_data()
                         st.rerun()

    # ---------------------------------------------------------
    # TAB 2: PORTFOLIO MANAGEMENT
    # ---------------------------------------------------------
    with tab2:
        # Input Form
        with st.expander("💼 Catat Transaksi Baru", expanded=not st.session_state.user_data["portfolio"]):
            with st.form("add_portfolio"):
                c1, c2 = st.columns(2)
                p_sym = c1.text_input("Kode Saham", placeholder="BBCA.JK / NVDA").upper().strip()
                p_curr_raw = c2.selectbox("Mata Uang", ["IDR (Rupiah)", "USD (Dollar)"])
                
                c3, c4 = st.columns(2)
                # Note: Using static label and step to prevent widget reset (State Lag issue)
                p_price = c3.number_input("Harga Beli", min_value=0.0, step=0.01, format="%.2f")
                p_qty = c4.number_input("Jumlah (Lot/Lembar)", min_value=1, step=1, help="Total lembar saham")

                if st.form_submit_button("Simpan Transaksi", use_container_width=True):
                    # Resolve currency logic post-submission
                    final_curr_code = "IDR" if "IDR" in p_curr_raw else "USD"
                    
                    if p_sym and p_price > 0 and p_qty > 0:
                        st.session_state.user_data["portfolio"].append({
                            "symbol": p_sym, 
                            "buy_price": p_price, 
                            "quantity": p_qty, 
                            "currency": final_curr_code
                        })
                        save_user_data()
                        st.success("Transaksi disimpan!")
                        st.rerun()

        portfolio = st.session_state.user_data["portfolio"]
        
        # Portfolio Calculation Logic
        if portfolio:
            pf_tickers = list(set([item["symbol"] for item in portfolio]))
            pf_batch = get_batch_stock_data(pf_tickers, period="1d")
            
            total_inv_idr, total_val_idr = 0, 0
            total_inv_usd, total_val_usd = 0, 0
            
            processed_data = []

            for index, item in enumerate(portfolio):
                sym = item["symbol"]
                currency = item.get("currency", "USD")
                buy_price = item["buy_price"]
                qty = item["quantity"]
                
                # --- Price Retrieval Logic ---
                curr_price = None 
                
                # Strategy 1: Batch Data
                try:
                    if not pf_batch.empty:
                        if isinstance(pf_batch.columns, pd.MultiIndex) and sym in pf_batch.columns.levels[0]:
                            val = pf_batch[sym]["Close"].iloc[-1]
                            if not pd.isna(val): curr_price = val
                        elif len(pf_tickers) == 1 and "Close" in pf_batch.columns:
                            val = pf_batch["Close"].iloc[-1]
                            if not pd.isna(val): curr_price = val
                except Exception: 
                    pass

                # Strategy 2: Individual Fetch Fallback
                if curr_price is None or pd.isna(curr_price):
                    try:
                        ticker_data = yf.Ticker(sym).history(period="1d")
                        if not ticker_data.empty:
                            curr_price = ticker_data["Close"].iloc[-1]
                    except Exception: 
                        pass
                
                # Error Handling: Default to buy_price to prevent NaN propagation
                is_error = False
                if curr_price is None or pd.isna(curr_price):
                    curr_price = buy_price 
                    is_error = True

                # Financial Calculations
                inv_val = buy_price * qty
                curr_val = curr_price * qty
                gain_loss = curr_val - inv_val
                gain_pct = (gain_loss / inv_val) * 100 if inv_val > 0 else 0

                # Currency Aggregation
                if currency == "IDR":
                    total_inv_idr += inv_val
                    total_val_idr += curr_val
                else:
                    total_inv_usd += inv_val
                    total_val_usd += curr_val

                processed_data.append({
                    "index": index,
                    "symbol": sym,
                    "currency": currency,
                    "buy_price": buy_price,
                    "curr_price": curr_price,
                    "qty": qty,
                    "curr_val": curr_val,
                    "gain_loss": gain_loss,
                    "gain_pct": gain_pct,
                    "is_error": is_error
                })

            # --- Metrics Display ---
            st.markdown("### 📊 Ringkasan")
            
            # IDR Summary
            if total_inv_idr > 0:
                pl_idr = total_val_idr - total_inv_idr
                pl_pct_idr = (pl_idr / total_inv_idr * 100)
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Investasi (IDR)", f"Rp {total_inv_idr:,.0f}")
                c2.metric("Nilai Aset (IDR)", f"Rp {total_val_idr:,.0f}", delta=f"{pl_idr:,.0f}")
                c3.metric("Imbal Hasil (IDR)", f"{pl_pct_idr:+.2f}%")
                st.divider()

            # USD Summary
            if total_inv_usd > 0:
                pl_usd = total_val_usd - total_inv_usd
                pl_pct_usd = (pl_usd / total_inv_usd * 100)
                d1, d2, d3 = st.columns(3)
                d1.metric("Total Investasi (USD)", f"${total_inv_usd:,.2f}")
                d2.metric("Nilai Aset (USD)", f"${total_val_usd:,.2f}", delta=f"{pl_usd:,.2f}")
                d3.metric("Imbal Hasil (USD)", f"{pl_pct_usd:+.2f}%")

            # --- Portfolio Table Rendering ---
            st.markdown("### 📜 Rincian Aset (Kelola)")
            
            # Table Header
            h1, h2, h3, h4, h5 = st.columns([1.5, 1.5, 1.5, 2, 0.5])
            h1.markdown("**Saham**")
            h2.markdown("**Harga**")
            h3.markdown("**Qty**")
            h4.markdown("**Profit/Loss**")
            h5.markdown("**Aksi**")
            st.markdown("<hr style='margin: 5px 0'>", unsafe_allow_html=True)

            # Table Rows
            for item in processed_data:
                fmt = "Rp {:,.0f}" if item['currency'] == "IDR" else "$ {:,.2f}"
                
                # Conditional Formatting
                color = "#16a34a" if item['gain_loss'] >= 0 else "#dc2626"
                if item['is_error']: color = "#eab308"

                # Row Layout
                r1, r2, r3, r4, r5 = st.columns([1.5, 1.5, 1.5, 2, 0.5])
                
                # Column 1: Asset Info
                r1.markdown(f"**{item['symbol']}**<br><span style='font-size:12px; color:#888'>Beli: {fmt.format(item['buy_price'])}</span>", unsafe_allow_html=True)
                
                # Column 2: Market Price
                err_mark = "⚠️" if item['is_error'] else ""
                r2.markdown(f"{fmt.format(item['curr_price'])} {err_mark}")
                
                # Column 3: Quantity
                r3.markdown(f"{item['qty']}")
                
                # Column 4: PnL
                pl_txt = f"{fmt.format(item['gain_loss'])} ({item['gain_pct']:+.2f}%)"
                r4.markdown(f"<span style='color:{color}; font-weight:bold'>{pl_txt}</span>", unsafe_allow_html=True)
                
                # Column 5: Delete Button
                if r5.button("🗑️", key=f"del_pf_{item['index']}", help=f"Hapus {item['symbol']}"):
                    st.session_state.user_data["portfolio"].pop(item['index'])
                    save_user_data()
                    st.rerun()
                
                st.markdown("<div class='stock-row'></div>", unsafe_allow_html=True)

        else:
            st.info("Portofolio masih kosong.")