import os, json, tempfile, shutil
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from modules.stock_tools import get_batch_stock_data, yahoo_status

# 🎨 CSS Styling
st.markdown("""
<style>
.stock-card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 15px;
    transition: all 0.3s ease;
}
.stock-card:hover {
    border-color: #facc15;
    transform: translateY(-3px);
    box-shadow: 0 4px 12px rgba(250,204,21,0.15);
}
</style>
""", unsafe_allow_html=True)

# Core Functions: Load & Save Data
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "user_data.json")

def ensure_data_loaded():
    if "user_data" not in st.session_state:
        st.session_state.user_data = {"watchlist": [], "portfolio": []}
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    st.session_state.user_data = json.load(f)
            except: pass

def save_user_data():
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, dir=DATA_DIR) as tmp:
            json.dump(st.session_state.user_data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.move(tmp.name, DATA_FILE)
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")

# 💼 Halaman Watchlist + Portfolio Mode
def show_watchlist():
    ensure_data_loaded()
    
    st.markdown("<h1>📋 Aset Saya</h1>", unsafe_allow_html=True)
    st.caption("Kelola daftar pantau dan portofolio investasi kamu di sini.")
    
    tab1, tab2 = st.tabs(["👀 Watchlist", "💰 Portofolio"])

    # TAB 1: WATCHLIST
    with tab1:
        col_add, _ = st.columns([2, 1])
        with col_add:
            with st.form("add_watchlist"):
                c1, c2 = st.columns([3, 1])
                new_ticker = c1.text_input("Tambah Saham (kode):", placeholder="AAPL, BBCA.JK", label_visibility="collapsed").upper().strip()
                if c2.form_submit_button("➕ Tambah", use_container_width=True):
                    if new_ticker and new_ticker not in st.session_state.user_data["watchlist"]:
                        st.session_state.user_data["watchlist"].append(new_ticker)
                        save_user_data()
                        st.rerun()

        watchlist = st.session_state.user_data["watchlist"]
        if watchlist:
            # ambil data 1 bulan penuh
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
                    except: pass

                    if not data.empty and "Close" in data.columns and len(data) >= 2:
                        # Hitung Mundur 1 Bulan
                        last = data["Close"].iloc[-1]
                        start_of_month = data["Close"].iloc[0]
                        
                        change = last - start_of_month
                        pct_change = (change / start_of_month) * 100 if start_of_month != 0 else 0
                        
                        color = "#16a34a" if change >= 0 else "#dc2626"
                        icon = "▲" if change >= 0 else "▼"

                        st.markdown(f"""
                        <div class="stock-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h3 style="color:#facc15; margin:0;">{ticker}</h3>
                                <span style="font-size:18px; font-weight:bold;">${last:,.2f}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">
                                <span style="color:{color}; font-weight:600;">{icon} {pct_change:+.2f}%</span>
                                <span style="color:#9da7b2; font-size:12px;">1 Bulan</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Grafik Interaktif
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=data.index, 
                            y=data["Close"], 
                            mode='lines', 
                            line=dict(color=color, width=2), 
                            fill='tozeroy',
                            fillcolor=f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.1)",
                            name="Harga",
                            hovertemplate="$%{y:.2f}<extra></extra>"
                        ))
                        
                        fig.update_layout(
                            height=80,
                            margin=dict(l=0,r=0,t=5,b=0), 
                            xaxis=dict(visible=False, fixedrange=True),
                            yaxis=dict(visible=False, fixedrange=True),
                            paper_bgcolor='rgba(0,0,0,0)', 
                            plot_bgcolor='rgba(0,0,0,0)',
                            hovermode="x unified"
                        )
                        
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                    else:
                         st.markdown(f"""<div class="stock-card" style="border-color:#dc2626;"><h3 style="color:#9da7b2; margin:0;">{ticker}</h3><p style="color:#dc2626;">Gagal memuat data</p></div>""", unsafe_allow_html=True)

                    if st.button(f"🗑️ Hapus", key=f"del_{ticker}"):
                         st.session_state.user_data["watchlist"].remove(ticker)
                         save_user_data()
                         st.rerun()

    # TAB 2: PORTOFOLIO
    with tab2:
        with st.expander("💼 Catat Transaksi Baru", expanded=not st.session_state.user_data["portfolio"]):
            with st.form("add_portfolio"):
                c1, c2, c3 = st.columns(3)
                p_sym = c1.text_input("Kode Saham", placeholder="NVDA").upper().strip()
                p_price = c2.number_input("Harga Beli ($)", min_value=0.0, step=0.1)
                p_qty = c3.number_input("Jumlah (Lembar)", min_value=1, step=1)
                if st.form_submit_button("Simpan Transaksi", use_container_width=True):
                    if p_sym and p_price > 0 and p_qty > 0:
                        st.session_state.user_data["portfolio"].append({
                            "symbol": p_sym, "buy_price": p_price, "quantity": p_qty
                        })
                        save_user_data()
                        st.success("Transaksi berhasil dicatat!")
                        st.rerun()

        portfolio = st.session_state.user_data["portfolio"]
        if portfolio:
            pf_tickers = list(set([item["symbol"] for item in portfolio]))
            pf_batch = get_batch_stock_data(pf_tickers, period="1d")
            total_val, total_inv = 0, 0
            pf_table = []
            for item in portfolio:
                sym = item["symbol"]
                curr_price = item["buy_price"]
                try:
                    if not pf_batch.empty:
                        if isinstance(pf_batch.columns, pd.MultiIndex) and sym in pf_batch.columns.levels[0]:
                            curr_price = pf_batch[sym]["Close"].iloc[-1]
                        elif len(pf_tickers) == 1 and "Close" in pf_batch.columns:
                            curr_price = pf_batch["Close"].iloc[-1]
                except: pass
                inv_val = item["buy_price"] * item["quantity"]
                curr_val = curr_price * item["quantity"]
                gain_loss = curr_val - inv_val
                gain_pct = (gain_loss / inv_val) * 100 if inv_val > 0 else 0
                total_inv += inv_val
                total_val += curr_val
                pf_table.append({"Saham": sym, "Avg Beli": item["buy_price"], "Harga Kini": curr_price, "Qty": item["quantity"], "Nilai ($)": curr_val, "P/L ($)": gain_loss, "P/L (%)": gain_pct})

            tot_pl = total_val - total_inv
            tot_pl_pct = (tot_pl / total_inv * 100) if total_inv > 0 else 0
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Investasi", f"${total_inv:,.2f}")
            m2.metric("Nilai Sekarang", f"${total_val:,.2f}", delta=f"{tot_pl:,.2f}")
            m3.metric("Total Profit/Loss", f"{tot_pl_pct:+.2f}%")

            st.dataframe(pd.DataFrame(pf_table).style.format({"Avg Beli": "${:,.2f}", "Harga Kini": "${:,.2f}", "Nilai ($)": "${:,.2f}", "P/L ($)": "${:+,.2f}", "P/L (%)": "{:+.2f}%"}).applymap(lambda x: f'color: {"#16a34a" if x >= 0 else "#dc2626"}', subset=["P/L ($)", "P/L (%)"]), use_container_width=True, hide_index=True)
            if st.button("⚠️ Reset Portofolio"):
                st.session_state.user_data["portfolio"] = []
                save_user_data()
                st.rerun()
        else:
            st.info("Portofolio masih kosong.")