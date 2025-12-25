import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from modules.ui_assets import DASHBOARD_CSS, ICONS

"""
DASHBOARD VIEW MODULE
---------------------
Responsibility: Handles all UI rendering and HTML generation.
Layout: 
1. Hero Header (FinAssist Intelligence)
2. Ticker Tape
3. Global News
4. Local News
5. Weekly Movers
"""

def render_global_styles():
    """Injects the global CSS from ui_assets."""
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

def render_hero_header():
    """
    Renders the MAIN TITLE (FinAssist Intelligence) at the very top.
    Replaces the old 'Market Dashboard'.
    """
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom: 5px;">
        <div style="color:#facc15; font-size: 2rem;">{ICONS['activity']}</div>
        <div>
            <h1 style="margin:0; font-size: 32px; display:inline;">FinAssist Intelligence</h1>
            <div style="font-size: 14px; color: #8b949e; margin-top:5px;">
                Monitoring global markets, news, and stock trends in a unified view.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_ticker_bar(ticker_items, status_msg):
    """
    Renders the horizontal ticker tape directly under the header.
    """
    # Status Connection
    st.markdown(f"""
    <div style="text-align:right; font-size:11px; color:#30363d; margin-bottom:5px;">
        {ICONS['wifi']} Feed: <span style="color:#2ea043;">{status_msg}</span>
    </div>
    """, unsafe_allow_html=True)
    
    ticker_html = ""
    if ticker_items:
        for item in ticker_items:
            # Safe Extraction & Type Conversion
            change = item.get('change', item.get('change_pct', 0))
            value = item.get('value', item.get('price', 0))
            name = item.get('name', item.get('symbol', '???'))

            try:
                if hasattr(change, 'item'): change = change.item()
                if hasattr(value, 'item'): value = value.item()
                change = float(change)
                value = float(value)
            except:
                change = 0.0
                value = 0.0

            color = "#2ea043" if change >= 0 else "#da3633"
            arrow_icon = ICONS["trending_up"] if change >= 0 else ICONS["trending_down"]
            
            arrow_display = f"<span style='color:{color}; display:inline-flex; align-items:center; gap:2px;'>{arrow_icon} {change:.2f}%</span>"
            
            ticker_html += f"<span class='ticker-item'><span style='color:#facc15; font-weight:bold;'>{name}</span> <span style='color:#e6edf3'>${value:,.2f}</span> {arrow_display}</span>"

    st.markdown(f"""
        <div class="ticker-container" style="margin-top:0px;">
            <div class="ticker-content">{ticker_html}</div>
        </div>
    """, unsafe_allow_html=True)

def render_news_section(news_data):
    """Renders the GLOBAL news cards section."""
    # Header Global News
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; margin-top:20px;">
            <div style="color:#facc15;">{ICONS['news']}</div>
            <h2 style="margin:0; font-size: 1.5rem;">Global Market News</h2>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<div class='section-divider' style='margin: 10px 0;'></div>", unsafe_allow_html=True)

    if news_data:
        for article in news_data[:4]:
            title = article.get('title', 'No Title')
            desc = article.get('desc', article.get('description', ''))
            source = article.get('source', 'Unknown')
            published = article.get('published', '')
            url = article.get('url', '#')

            st.markdown(f"""
            <div class="news-card">
                <h3 style="font-size:1.1rem; margin-top:0; color:#58a6ff;">{title}</h3>
                <p style="color:#8b949e; font-size:0.9rem; line-height:1.5;">{desc[:200]}...</p>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                    <span style="font-size:12px; color:#facc15; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">{source} • {published}</span>
                    <a href="{url}" target="_blank" style="display:flex; align-items:center; gap:5px;">
                        Read Story {ICONS['link']}
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No global news available.")

def render_local_news_section(local_news_data):
    """Renders the INDONESIA/LOCAL news section."""
    
    # Header Local News
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; margin-top: 30px;">
            <div style="color:#2ea043;">{ICONS['briefcase']}</div>
            <h2 style="margin:0; font-size: 1.5rem;">Indonesia Market Pulse (IDX)</h2>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<div class='section-divider' style='margin: 10px 0;'></div>", unsafe_allow_html=True)
    
    if local_news_data:
        for i in range(0, len(local_news_data), 2):
            c1, c2 = st.columns(2)
            
            def _render_card(col, article):
                with col:
                    title = article.get('title', 'No Title')
                    desc = article.get('desc', '')[:150] + "..." if article.get('desc') else "Berita pasar terkini."
                    source = article.get('source', 'Local Media')
                    published = article.get('published', '')
                    url = article.get('url', '#')

                    st.markdown(f"""
                    <div class="news-card" style="border-left: 3px solid #2ea043;">
                        <h3 style="font-size:1.1rem; margin-top:0; color:#58a6ff;">{title}</h3>
                        <p style="color:#8b949e; font-size:0.9rem; line-height:1.5;">{desc}</p>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                            <span style="font-size:12px; color:#2ea043; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">{source} • {published}</span>
                            <a href="{url}" target="_blank" style="display:flex; align-items:center; gap:5px;">Baca {ICONS['link']}</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            if i < len(local_news_data):
                _render_card(c1, local_news_data[i])
            if i + 1 < len(local_news_data):
                _render_card(c2, local_news_data[i+1])
    else:
        st.info("Belum ada update pasar lokal terkini.")

def render_weekly_movers(trending_data):
    """Renders the top movers cards. MOVED TO BOTTOM."""
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; margin-top: 40px;">
            <div style="color:#facc15;">{ICONS['bar_chart']}</div>
            <h2 style="margin:0; font-size: 1.5rem;">Weekly Top Movers</h2>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<div class='section-divider' style='margin: 10px 0;'></div>", unsafe_allow_html=True)

    if not trending_data:
        st.warning("High traffic to data source. Please refresh shortly.")
        return

    limit = min(len(trending_data), 4)
    t_cols = st.columns(limit)
    
    for i in range(limit):
        ticker, delta, data = trending_data[i]
        
        if data.empty or "Close" not in data.columns:
            continue

        if hasattr(delta, 'item'): delta = delta.item()
        delta = float(delta)

        latest_price = data["Close"].iloc[-1]
        color = "#2ea043" if delta >= 0 else "#da3633"
        icon_svg = ICONS["trending_up"] if delta >= 0 else ICONS["trending_down"]
        sma5 = data["Close"].rolling(window=5).mean()

        with t_cols[i]:
            st.markdown(f"""
            <div class="stock-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="color:#facc15; font-size:16px; margin:0;">{ticker}</h3>
                    <span style="font-size:12px; color:#8b949e;">7D</span>
                </div>
                <p style="font-size:20px; font-weight:700; margin:5px 0;">${latest_price:,.2f}</p>
                <p style="color:{color}; font-weight:600; font-size:13px; display:flex; align-items:center; gap:4px;">
                    {icon_svg} {delta:+.2f}%
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Sparkline
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data["Close"], mode="lines", 
                                     line=dict(color=color, width=2), fill='tozeroy',
                                     fillcolor=f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.1)"))
            if not sma5.isna().all():
                fig.add_trace(go.Scatter(x=data.index, y=sma5, mode="lines", line=dict(color="#facc15", width=1, dash="dot")))
                  
            fig.update_layout(height=60, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False),
                              showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

def render_footer():
    """Renders the CTA footer."""
    st.markdown("<div class='section-divider' style='margin-top: 50px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style='text-align:center; margin-top:20px; margin-bottom:20px;'>
            <p style="font-size:16px; color:#8b949e;">{ICONS['bot']} Need deeper analysis on these stocks?</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Ask AI Assistant Now", use_container_width=True, type="primary"):
            st.session_state.active_page = "Chatbot"
            st.rerun()