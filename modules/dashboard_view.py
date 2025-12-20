import streamlit as st
import plotly.graph_objects as go
from modules.ui_assets import DASHBOARD_CSS, ICONS

"""
DASHBOARD VIEW MODULE
---------------------
Responsibility: Handles all UI rendering and HTML generation.
"""

def render_global_styles():
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

def render_ticker_bar(ticker_items, status_msg):
    st.caption(f"{ICONS['wifi']} Data Feed: {status_msg}", unsafe_allow_html=True)
    
    ticker_html = ""
    if ticker_items:
        for item in ticker_items:
            change = item.get('change', item.get('change_pct', 0))
            value = item.get('value', item.get('price', 0))
            name = item.get('name', item.get('symbol', '???'))

            color = "#2ea043" if change > 0 else "#da3633"
            arrow_icon = ICONS["trending_up"] if change > 0 else ICONS["trending_down"]
            
            arrow_display = f"<span style='color:{color}; display:inline-flex; align-items:center;'>{arrow_icon} {change:.2f}%</span>"
            ticker_html += f"<span class='ticker-item'><span style='color:#8b949e'>{name}:</span> {arrow_display} <span style='color:#e6edf3'>${value:.2f}</span></span>"

    st.markdown(f"""
        <div class="ticker-container">
            <div class="ticker-content">{ticker_html}</div>
        </div>
    """, unsafe_allow_html=True)

def render_news_section(news_data):
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
            <div style="color:#facc15;">{ICONS['activity']}</div>
            <h1 style="margin:0; display:inline;">FinAssist Intelligence</h1>
        </div>
        """, unsafe_allow_html=True)
    
    st.caption("Monitoring global markets, news, and stock trends in a unified view.")
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="color:#facc15;">{ICONS['news']}</div>
            <h2 style="margin:0; font-size: 1.5rem;">Global Market News</h2>
        </div>
    """, unsafe_allow_html=True)

    if news_data:
        for article in news_data[:5]:
            title = article.get('title', 'No Title')
            desc = article.get('desc', article.get('description', ''))
            source = article.get('source', 'Unknown')
            published = article.get('published', '')
            url = article.get('url', '#')

            st.markdown(f"""
            <div class="news-card">
                <h3 style="font-size:1.1rem; margin-top:0;">{title}</h3>
                <p style="color:#8b949e; font-size:0.9rem; line-height:1.5;">{desc}</p>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                    <span style="font-size:12px; color:#facc15; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">{source} • {published}</span>
                    <a href="{url}" target="_blank" style="display:flex; align-items:center; gap:5px;">
                        Read Full Story {ICONS['link']}
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No latest news available.")

def render_weekly_movers(trending_data):
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="color:#facc15;">{ICONS['bar_chart']}</div>
            <h2 style="margin:0; font-size: 1.5rem;">Weekly Top Movers</h2>
        </div>
    """, unsafe_allow_html=True)

    if not trending_data:
        st.warning("High traffic to data source. Please refresh shortly.")
        return

    limit = min(len(trending_data), 4)
    t_cols = st.columns(limit)
    
    for i in range(limit):
        ticker, delta, data = trending_data[i]
        
        if data.empty or "Close" not in data.columns:
            continue

        latest_price = data["Close"].iloc[-1]
        color = "#2ea043" if delta > 0 else "#da3633"
        icon_svg = ICONS["trending_up"] if delta > 0 else ICONS["trending_down"]
        sma5 = data["Close"].rolling(window=5).mean()

        with t_cols[i]:
            st.markdown(f"""
            <div class="stock-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="color:#facc15; font-size:16px; margin:0;">{ticker}</h3>
                    <span style="font-size:12px; color:#8b949e;">7D</span>
                </div>
                <p style="font-size:20px; font-weight:700; margin:5px 0;">${latest_price:.2f}</p>
                <p style="color:{color}; font-weight:600; font-size:13px; display:flex; align-items:center; gap:4px;">
                    {icon_svg} {delta:.2f}%
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data["Close"], mode="lines", 
                                     line=dict(color=color, width=2), name="Price"))
            
            if not sma5.isna().all():
                fig.add_trace(go.Scatter(x=data.index, y=sma5, mode="lines", 
                                         line=dict(color="#facc15", width=1, dash="dot"), name="SMA5"))
                  
            fig.update_layout(height=80, margin=dict(l=0, r=0, t=0, b=0),
                              xaxis=dict(visible=False), yaxis=dict(visible=False),
                              showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

def render_footer():
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("""
        <div style='text-align:center; margin-top:30px; margin-bottom:20px;'>
            <p style="font-size:16px; color:#8b949e;">Need deeper analysis on the stocks above?</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Ask AI Assistant Now", use_container_width=True, type="primary"):
            st.session_state.active_page = "Chatbot"
            st.rerun()