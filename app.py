import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import feedparser
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
st.set_page_config(page_title="RE Command Center", layout="wide", page_icon="⚡")

# Auto-refresh every 5 minutes
st_autorefresh(interval=300 * 1000, key="newsrefresh")

# --- CUSTOM CSS FOR "PRO" LOOK ---
st.markdown("""
<style>
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #2e86c1;
    }
    /* News Cards */
    .news-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2e86c1;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 12px;
        transition: transform 0.2s;
    }
    .news-card:hover {
        transform: scale(1.01);
    }
    .tag {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    .timestamp {
        color: #888;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- BACKEND: FETCH DATA ---
@st.cache_data(ttl=300) # Cache for 5 mins
def get_feed_data():
    # STRICT MODE LINKS
    rss_feeds = {
        "Solar": "https://news.google.com/rss/search?q=(solar+energy+OR+photovoltaic+OR+solar+power)+-oil+-gas+-coal+-nuclear+-shares+when:1d&hl=en-US&gl=US&ceid=US:en",
        "Wind": "https://news.google.com/rss/search?q=(wind+energy+OR+wind+power+OR+offshore+wind)+-weather+-storm+-oil+-gas+-coal+when:1d&hl=en-US&gl=US&ceid=US:en",
        "Storage": "https://news.google.com/rss/search?q=(battery+storage+OR+energy+storage+system+OR+BESS+OR+pumped+hydro)+-mobile+-phone+-car+-scooter+when:1d&hl=en-US&gl=US&ceid=US:en",
        "Hydrogen": "https://news.google.com/rss/search?q=(green+hydrogen+OR+clean+hydrogen+OR+green+ammonia+OR+electrolyzer)+-oil+-gas+-coal+when:1d&hl=en-US&gl=US&ceid=US:en",
        "Manufacturing": "https://news.google.com/rss/search?q=(solar+manufacturing+OR+PV+manufacturing+OR+solar+module+production+OR+solar+exports+OR+ALMM+OR+PLI)+-textile+-auto+-oil+-gas+when:1d&hl=en-US&gl=US&ceid=US:en",
        "India Grid": "https://news.google.com/rss/search?q=(MNRE+OR+SECI+OR+Power+Grid+OR+Transmission+OR+Tariff+OR+Discom+OR+Electricity+Authority+OR+Tender+OR+Auction+OR+PPA)+-coal+-thermal+-oil+-gas+-nuclear+-election+-congress+-bjp+-cricket+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
    }
    
    items = []
    for sector, url in rss_feeds.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            # Parse published date to datetime object for plotting
            try:
                dt = datetime(*entry.published_parsed[:6])
            except:
                dt = datetime.now()
                
            items.append({
                "Title": entry.title,
                "Link": entry.link,
                "Source": entry.source.title if 'source' in entry else "Google News",
                "Published": dt,
                "Sector": sector
            })
    return pd.DataFrame(items)

# Load Data
df = get_feed_data()

# --- DASHBOARD HEADER ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("⚡ Renewable Energy Command Center")
    st.markdown("Live Intelligence Dashboard • *Strict Filter Mode Active*")
with c2:
    if not df.empty:
        st.metric("Total Intelligence", f"{len(df)} Articles", delta="Live Update")

st.divider()

if not df.empty:
    # --- ROW 1: ADVANCED VISUALS ---
    col_viz1, col_viz2 = st.columns([1, 1])

    with col_viz1:
        st.subheader("🎯 Sector & Source Hierarchy")
        # SUNBURST CHART: Shows Sector -> Source breakdown interactively
        fig_sun = px.sunburst(
            df, 
            path=['Sector', 'Source'], 
            title="Click sections to drill down",
            color='Sector',
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_sun.update_layout(height=400, margin=dict(t=40, l=0, r=0, b=0))
        st.plotly_chart(fig_sun, use_container_width=True)

    with col_viz2:
        st.subheader("🕒 News Timeline (Last 24h)")
        # SCATTER PLOT: Shows when news broke
        fig_time = px.scatter(
            df, 
            x="Published", 
            y="Sector", 
            color="Sector", 
            hover_data=["Title"],
            size_max=10,
            title="News Arrival Time"
        )
        fig_time.update_layout(height=400, showlegend=False, xaxis_title="Time of Day")
        st.plotly_chart(fig_time, use_container_width=True)

    # --- ROW 2: DETAILED NEWS FEED ---
    st.divider()
    
    # Filter Controls
    c_filter1, c_filter2 = st.columns([3, 1])
    with c_filter1:
        search = st.text_input("🔍 Search Headlines", placeholder="e.g. Adani, Tender, PLI...")
    with c_filter2:
        selected_sector = st.selectbox("Filter Sector", ["All"] + list(df['Sector'].unique()))

    st.subheader("📰 Live Feed")

    # Apply Filters
    dff = df.copy()
    if selected_sector != "All":
        dff = dff[dff['Sector'] == selected_sector]
    if search:
        dff = dff[dff['Title'].str.contains(search, case=False)]

    # Display Cards
    dff = dff.sort_values(by="Published", ascending=False)
    
    for _, row in dff.iterrows():
        # Clean Date Format
        time_str = row['Published'].strftime("%H:%M")
        date_str = row['Published'].strftime("%d %b")
        
        st.markdown(f"""
        <div class="news-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="tag">{row['Sector']}</span>
                <span class="timestamp">{date_str} • {time_str}</span>
            </div>
            <h4 style="margin-top:8px; margin-bottom:5px;">
                <a href="{row['Link']}" target="_blank" style="text-decoration:none; color:#1a1a1a;">{row['Title']}</a>
            </h4>
            <div style="font-size:13px; color:#555;">Source: <b>{row['Source']}</b></div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.warning("Waiting for data... (Check internet connection)")
