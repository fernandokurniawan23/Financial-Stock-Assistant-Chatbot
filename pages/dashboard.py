import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from modules.stock_tools import get_stock_data_safe, yahoo_status
from modules.news_tools import get_latest_news

# =====================================================
# 🎨 DASHBOARD UTAMA
# =====================================================
def show_dashboard():
    # ========== Custom CSS: Tema Bloomberg Style ==========
    st.markdown("""
        <style>
        body {
            background-color: #0d1117;
            color: #e6edf3;
            font-family: 'Segoe UI', sans-serif;
        }
        .main { background-color: #0d1117; }
        h1, h2, h3 {
            color: #facc15;
            font-weight: 700;
        }
        .news-card, .stock-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        .news-card:hover, .stock-card:hover {
            border-color: #facc15;
            transform: translateY(-3px);
            box-shadow: 0px 4px 12px rgba(250, 204, 21, 0.15);
        }
        a { color: #58a6ff !important; text-decoration: none !important; }
        a:hover { text-decoration: underline !important; }
        .section-divider {
            border-bottom: 1px solid #30363d;
            margin: 20px 0;
        }
        /* 🌐 Bloomberg-style ticker bar */
        .ticker-container {
            width: 100%;
            overflow: hidden;
            white-space: nowrap;
            background-color: #111418;
            border-bottom: 1px solid #30363d;
            padding: 6px 0;
        }
        .ticker-content {
            display: inline-block;
            animation: tickerScroll 25s linear infinite;
            font-size: 15px;
        }
        @keyframes tickerScroll {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        .ticker-item {
            margin-right: 50px;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    # =====================================================
    # 💹 Real-Time Market Ticker Bar
    # =====================================================
    st.caption(f"📡 Status Data: {yahoo_status()}")
    ticker_symbols = {
        "AAPL": "Apple", "TSLA": "Tesla", "NVDA": "NVIDIA",
        "GOOGL": "Google", "AMZN": "Amazon",
        "BTC-USD": "Bitcoin", "GC=F": "Gold", "EURUSD=X": "Euro/USD"
    }

    ticker_html = ""
    for symbol, name in ticker_symbols.items():
        try:
            data = get_stock_data_safe(symbol, period="5d") # Ubah ke 5d agar lebih pasti ada data
            if len(data) < 2:
                continue
            latest = data["Close"].iloc[-1]
            prev = data["Close"].iloc[-2]
            change = ((latest - prev) / prev) * 100
            color = "#16a34a" if change > 0 else "#dc2626"
            arrow = "▲" if change > 0 else "▼"
            ticker_html += f"<span class='ticker-item'>{name}: <span style='color:{color};'>{arrow} {change:.2f}%</span> ${latest:.2f}</span>"
        except Exception:
            continue

    st.markdown(f"""
        <div class="ticker-container">
            <div class="ticker-content">{ticker_html}</div>
        </div>
    """, unsafe_allow_html=True)

    # Section 1: Berita Pasar Global
    st.markdown("<h1>📊 FinAssist Market Intelligence</h1>", unsafe_allow_html=True)
    st.caption("FinAssist pantau pasar global, berita, dan tren saham dalam satu tampilan cerdas.")

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("<h2>📰 Berita Pasar Global Hari Ini</h2>", unsafe_allow_html=True)

    news = get_latest_news()
    if news and "articles" in news:
        for article in news["articles"][:4]:
            title = article.get("title", "Tanpa Judul")
            source = article.get("source", {}).get("name", "Unknown Source")
            url = article.get("url", "#")
            desc = article.get("description", "") or ""
            published = article.get("publishedAt", "")[:10] if article.get("publishedAt") else "N/A"
            
            st.markdown(f"""
            <div class="news-card">
                <h3>{title}</h3>
                <p style="color:#9da7b2;">{desc[:150] + '...' if len(desc) > 150 else desc}</p>
                <p style="font-size:13px; color:#58a6ff;">{source} • {published}</p>
                <a href="{url}" target="_blank">🔗 Baca selengkapnya</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Tidak ada berita terkini yang tersedia.")

    #Market Momentum Index (REAL-TIME FALLBACK)
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("<h2>🔥 Market Momentum Index</h2>", unsafe_allow_html=True)
    st.caption("Gabungan kenaikan harga dan frekuensi muncul di berita — menentukan saham paling 'panas' minggu ini.")

    candidates = pd.DataFrame()
    using_fallback = False

    # 1. Top Gainers dari Yahoo Finance
    try:
        from yahoo_fin import stock_info as si
        gainers_df = si.get_day_gainers().head(10)
        if not gainers_df.empty and '% Change' in gainers_df.columns:
             gainers_df = gainers_df.rename(columns={'% Change': 'Change (%)'})
             candidates = gainers_df[['Symbol', 'Name', 'Change (%)']].copy()
        else:
             raise ValueError("Data yahoo_fin kosong")
    except Exception:
        using_fallback = True

    # 2. Fallback dengan data asli
    if using_fallback or candidates.empty:
        fallback_tickers = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT", "META", "NFLX"]
        
        from modules.stock_tools import get_batch_stock_data
        batch_data = get_batch_stock_data(fallback_tickers, period="5d")
        
        fallback_rows = []
        if not batch_data.empty:
            for ticker in fallback_tickers:
                try:
                    # Ambil data per saham dari batch
                    stock_data = batch_data[ticker].copy() if ticker in batch_data.columns.levels[0] else pd.DataFrame()
                    # Handle jika batch hanya mengembalikan 1 saham
                    if stock_data.empty and len(fallback_tickers) == 1: stock_data = batch_data.copy()

                    if not stock_data.empty and len(stock_data) >= 2:
                        latest = stock_data["Close"].iloc[-1]
                        prev = stock_data["Close"].iloc[-2]
                        change = ((latest - prev) / prev) * 100
                        fallback_rows.append({"Symbol": ticker, "Name": ticker, "Change (%)": change})
                except:
                    continue
        candidates = pd.DataFrame(fallback_rows)

    # 3.Hitung Skor Momentum
    rows = []
    articles_text = ""
    news_count = 0
    
    if news and "articles" in news:
        news_count = len(news["articles"])
        articles_text = " ".join([
            str(a.get("title", "")) + " " + str(a.get("description", ""))
            for a in news["articles"]
        ]).upper()
    
    if news_count == 0:
        st.caption("⚠️ Tidak ada data berita yang berhasil dimuat. Skor momentum mungkin tidak akurat.")

    if not candidates.empty:
        for _, row in candidates.iterrows():
            try:
                sym = str(row.get("Symbol", "")).upper()
                change_val = row.get("Change (%)", 0)
                if isinstance(change_val, str):
                    change_raw = change_val.replace('%', '').replace('+', '').strip()
                    change = float(change_raw) if change_raw.replace('.', '', 1).isdigit() else 0.0
                else:
                    change = float(change_val)

                # Logika pencarian berita
                hits = 0
                if articles_text:
                    # Cari Ticker dengan spasi
                    hits += articles_text.count(f" {sym} ") 
                    hits += articles_text.count(f"({sym})")
                    
                    # Cari Nama Perusahaan
                    name_full = str(row.get("Name", "")).upper()
                    simple_name = name_full.replace(" INC.", "").replace(" CORP.", "").replace(" PLC", "").split()[0]
                    if len(simple_name) > 3:
                         hits += articles_text.count(simple_name)

                score = (change * 0.6) + (hits * 2.5)
                rows.append({
                    "Symbol": sym, "Company": row.get("Name", sym),
                    "Change (%)": change, "News Hits": hits, "Momentum Score": score
                })
            except Exception:
                continue

    momentum_df = pd.DataFrame(rows)
    if momentum_df.empty or "Momentum Score" not in momentum_df.columns:
        st.warning("⚠️ Data tidak cukup untuk Market Momentum Index saat ini.")
    else:
        top4 = momentum_df.sort_values(by="Momentum Score", ascending=False).head(4)
        cols = st.columns(len(top4))
        for i, (_, row) in enumerate(top4.iterrows()):
            change_pct = row.get("Change (%)", 0)
            color = "#16a34a" if change_pct > 0 else "#dc2626"
            icon = "▲" if change_pct > 0 else "▼"
            with cols[i]:
                st.markdown(f"""
                <div class="stock-card">
                    <h3 style="color:#facc15;">{row.get("Symbol", "?")}</h3>
                    <p style="font-size:14px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">{row.get("Company", "?")}</p>
                    <p style="font-size:20px; color:{color}; font-weight:600;">{icon} {change_pct:.2f}%</p>
                    <p style="font-size:12px; color:#9da7b2;">📰 {row.get("News Hits", 0)}x berita • 🔥 {row.get("Momentum Score", 0):.1f}</p>
                </div>
                """, unsafe_allow_html=True)

    # Saham Terpopuler Minggu Ini
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("<h2>📈 Saham Terpopuler Minggu Ini</h2>", unsafe_allow_html=True)

    candidate_stocks = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT", "META", "NFLX"]
    
    # optimalisasi Request
    # 1 request untuk 8 saham!
    from modules.stock_tools import get_batch_stock_data
    batch_data = get_batch_stock_data(candidate_stocks, period="1mo")

    trending_scores = []
    
    if not batch_data.empty:
        for ticker in candidate_stocks:
            try:
                # Ekstrak data per saham
                stock_data = batch_data[ticker].copy() if ticker in batch_data.columns.levels[0] else pd.DataFrame()
                
                # Fallback jika formatnya beda
                if stock_data.empty and len(candidate_stocks) == 1:
                     stock_data = batch_data.copy()

                if not stock_data.empty and "Close" in stock_data.columns and len(stock_data) >= 7:
                    latest = stock_data["Close"].iloc[-1]
                    prev_week = stock_data["Close"].iloc[-7] # Harga ~1 minggu lalu
                    delta = ((latest - prev_week) / prev_week) * 100
                    trending_scores.append((ticker, delta, stock_data))
            except Exception:
                continue

    # Tampilkan Data
    if trending_scores:
        top_trending = sorted(trending_scores, key=lambda x: x[1], reverse=True)[:4]
        t_cols = st.columns(len(top_trending))
        
        for i, (ticker, delta, data) in enumerate(top_trending):
            latest_price = data["Close"].iloc[-1]
            color = "#16a34a" if delta > 0 else "#dc2626"
            icon = "▲" if delta > 0 else "▼"
            
            # Hitung SMA5
            sma5 = data["Close"].rolling(window=5).mean()

            with t_cols[i]:
                st.markdown(f"""
                <div class="stock-card">
                    <h3 style="color:#facc15;">{ticker}</h3>
                    <p style="font-size:22px; font-weight:600;">${latest_price:.2f}</p>
                    <p style="color:{color}; font-weight:600;">{icon} {delta:.2f}% (7d)</p>
                </div>
                """, unsafe_allow_html=True)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=data.index, y=data["Close"], mode="lines", 
                                        line=dict(color=color, width=2), name="Price"))
                if not sma5.isna().all():
                    fig.add_trace(go.Scatter(x=data.index, y=sma5, mode="lines", 
                                            line=dict(color="#facc15", width=1, dash="dot"), name="SMA5"))
                     
                fig.update_layout(height=100, margin=dict(l=0, r=0, t=0, b=10),
                                  xaxis=dict(visible=False), yaxis=dict(visible=False),
                                  showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})
    else:
        st.warning("⚠️ Sedang lalu lintas tinggi ke bursa data. Coba refresh halaman dalam 1 menit.")

    # Footer & Navigation
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("""
        <div style='text-align:center; margin-top:30px; margin-bottom:20px;'>
            <p style="font-size:18px;">💬 Ingin analisis lebih dalam tentang saham di atas?</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🧠 Tanya AI Assistant Sekarang", use_container_width=True, type="primary"):
            st.session_state.active_page = "Chatbot"
            st.rerun()