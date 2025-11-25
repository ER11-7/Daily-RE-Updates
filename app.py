import streamlit as st
import pandas as pd
import feedparser
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="🔴 Live RE News Monitor", layout="wide")
CSV_FILE = "news_history.csv"
REFRESH_INTERVAL = 300  # Refresh every 300 seconds (5 minutes)

# --- 1. AUTO-REFRESH MECHANISM ---
# This forces the app to rerun every 5 minutes
count = st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="newsrefresh")

# --- 2. BACKEND FUNCTIONS ---

def load_data():
    """Loads the historical data from CSV if it exists."""
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame(columns=["Title", "Link", "Published", "Source", "Sector", "Timestamp"])

def save_data(df):
    """Saves the updated dataset to CSV."""
    df.to_csv(CSV_FILE, index=False)

def fetch_latest_news(existing_df):
   # --- STRICT MODE RSS FEEDS ---
    rss_feeds = {
        "Solar": "https://news.google.com/rss/search?q=(solar+energy+OR+photovoltaic+OR+solar+power)+-oil+-gas+-coal+-nuclear+-shares+when:1d&hl=en-US&gl=US&ceid=US:en",
        
        "Wind": "https://news.google.com/rss/search?q=(wind+energy+OR+wind+power+OR+offshore+wind)+-weather+-storm+-oil+-gas+-coal+when:1d&hl=en-US&gl=US&ceid=US:en",
        
        "Storage": "https://news.google.com/rss/search?q=(battery+storage+OR+energy+storage+system+OR+BESS+OR+pumped+hydro)+-mobile+-phone+-car+-scooter+when:1d&hl=en-US&gl=US&ceid=US:en",
        
        "Hydrogen": "https://news.google.com/rss/search?q=(green+hydrogen+OR+clean+hydrogen+OR+green+ammonia+OR+electrolyzer)+-oil+-gas+-coal+when:1d&hl=en-US&gl=US&ceid=US:en",
        
        "Manufacturing": "https://news.google.com/rss/search?q=(solar+manufacturing+OR+PV+manufacturing+OR+solar+module+production+OR+solar+exports+OR+ALMM+OR+PLI)+-textile+-auto+-oil+-gas+when:1d&hl=en-US&gl=US&ceid=US:en",
        
        # STRICT India Policy: Catches Grid/Tariff but blocks Coal/Politics/Thermal
        "India Power & Grid": "https://news.google.com/rss/search?q=(MNRE+OR+SECI+OR+Power+Grid+OR+Transmission+OR+Tariff+OR+Discom+OR+Electricity+Authority+OR+Tender+OR+Auction+OR+PPA)+-coal+-thermal+-oil+-gas+-nuclear+-election+-congress+-bjp+-cricket+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
    }
    
    new_items = []
    
    # Get list of existing links to prevent duplicates
    existing_links = set(existing_df['Link'].tolist())

    for sector, url in rss_feeds.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.link not in existing_links:
                new_items.append({
                    "Title": entry.title,
                    "Link": entry.link,
                    "Published": entry.published,
                    "Source": entry.source.title if 'source' in entry else "Google News",
                    "Sector": sector,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Capture when we found it
                })
                # Add to local set to avoid duplicates within the same fetch cycle
                existing_links.add(entry.link)
    
    if new_items:
        new_df = pd.DataFrame(new_items)
        # Combine old and new, put new ones at the top
        updated_df = pd.concat([new_df, existing_df], ignore_index=True)
        return updated_df, len(new_items)
    else:
        return existing_df, 0

# --- 3. MAIN DASHBOARD LOGIC ---

# Load History
df = load_data()

# Fetch Updates (This happens every auto-refresh)
with st.spinner('Checking for live updates...'):
    df, new_count = fetch_latest_news(df)
    save_data(df)

# --- 4. FRONTEND UI ---

st.title("🔴 Global RE Sector Live Monitor")
st.caption(f"Last Updated: {datetime.now().strftime('%H:%M:%S')} | Auto-refreshing every 5 mins")

# Top Metrics Row
c1, c2, c3 = st.columns(3)
c1.metric("Total News Database", f"{len(df)} articles")
c2.metric("New Since Last Check", f"{new_count}", delta_color="normal")
c3.metric("Latest Sector Activity", df.iloc[0]['Sector'] if not df.empty else "None")

st.divider()

# Controls
col_search, col_filter = st.columns([3, 1])
with col_search:
    search_query = st.text_input("🔍 Search Database (e.g., 'Adani', 'Tender', 'USA')", "")
with col_filter:
    sector_filter = st.multiselect("Filter Sector", df['Sector'].unique(), default=df['Sector'].unique())

# Apply Filters
view_df = df[df['Sector'].isin(sector_filter)]
if search_query:
    view_df = view_df[view_df['Title'].str.contains(search_query, case=False) | view_df['Source'].str.contains(search_query, case=False)]

# --- 5. THE LIVE FEED (Table View) ---
st.subheader("Live Feed")

# CSS for the 'Live' feel
st.markdown("""
<style>
    .new-badge {
        background-color: #d4edda;
        color: #155724;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Loop through data to display
for index, row in view_df.iterrows():
    # Determine if news is "Fresh" (less than 2 hours old since we found it)
    found_time = datetime.strptime(row['Timestamp'], "%Y-%m-%d %H:%M:%S")
    is_fresh = (datetime.now() - found_time).total_seconds() < 7200 # 2 hours
    
    with st.container():
        # Layout: Title on left, Metadata on right
        c_main, c_meta = st.columns([4, 1])
        
        with c_main:
            title_html = f"<a href='{row['Link']}' target='_blank' style='text-decoration:none; font-size:18px; font-weight:600; color:#333;'>{row['Title']}</a>"
            if is_fresh:
                title_html += " <span class='new-badge'>NEW</span>"
            st.markdown(title_html, unsafe_allow_html=True)
            st.markdown(f"<span style='color:grey; font-size:14px;'>{row['Summary'] if 'Summary' in row else ''}</span>", unsafe_allow_html=True)
            
        with c_meta:
            st.caption(f"**{row['Sector']}**")
            st.caption(f"{row['Source']}")
            st.caption(f"Found: {row['Timestamp'].split(' ')[1]}")
        
        st.divider()
