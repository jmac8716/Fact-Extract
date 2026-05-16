import streamlit as st
import json
import os
import glob

# --- UI CONFIGURATION ---
st.set_page_config(page_title="Z13 Global Intel", page_icon="📡", layout="wide")

# Custom CSS for that "Dark Mode Premium" or "Clean Enterprise" look
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.5rem; color: #007BFF; }
    .report-card { 
        padding: 2rem; 
        border-radius: 15px; 
        background-color: #ffffff; 
        border: 1px solid #e1e4e8;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# This tells the cloud to look in the NewsArchive folder inside your GitHub repo
archive_folder = "NewsArchive"

# --- DATA ENGINE ---
def load_data():
    archive_path = "./NewsArchive"
    
    if not os.path.exists(archive_path):
        return []
        
    files = glob.glob(os.path.join(archive_path, "*.json"))
    files.sort(reverse=True)
    # Ensure absolutely no None values pass through
    return [f for f in files if f is not None]

all_files = load_data()

# --- SIDEBAR ---
st.sidebar.title("Fact Archive")

# Pure string validation
valid_files = [f for f in all_files if f and isinstance(f, str)]

file_path = None
selected_name = None

if valid_files:
    valid_files.sort(reverse=True)
    
    # Double-check elements aren't empty strings or paths evaluating strangely
    file_display_names = [os.path.basename(f) for f in valid_files if f]
    
    if file_display_names:
        selected_name = st.sidebar.selectbox("Choose Report Time:", file_display_names, index=0)
    
    # Only try to stitch the path together if selectbox actually gave you a string string
    if selected_name:
        file_path = os.path.join("NewsArchive", selected_name)
else:
    st.sidebar.warning("No archives found. Check your GitHub 'NewsArchive' folder.")

# --- MAIN DASHBOARD ---
st.title("Fact Extract - 100% Concentrate")
st.divider()

# Core fallback tracking variable initialization
data = []

if file_path and os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            st.error("⚠️ Selected JSON report appears corrupted or incomplete.")
            data = []

    # Top level metrics
    m1, m2 = st.columns(2)
    if data:
        m1.metric("Current Articles", len(data))
        unique_cats = len(set(entry.get('category', 'Unknown') for entry in data))
        m2.metric("Categories", unique_cats)
    else:    
        st.warning("No data found in this report.")

    st.write("---")
else:
    if file_path:
        st.error(f"⚠️ Report file path specified but could not be located on disk: {file_path}")

# --- MAIN DISPLAY AREA ---
if data:
    for entry in data:
        category = entry.get('category', 'GENERAL').upper()
        saved_title = entry.get('title')
        article_url = entry.get('url', '')
        
        if saved_title and "http" not in saved_title:
            display_title = saved_title.upper()
        else:
            raw_slug = article_url.split('/')[-1].split('?')[0] if article_url else "unknown-source"
            display_title = raw_slug.replace(".html", "").replace("-", " ").replace("_", " ").upper()
        
        st.markdown(f":blue[**{category}**]")
        st.subheader(f"{display_title}")
    
        content_to_display = entry.get('report', entry.get('facts', "No content available"))
        st.markdown(content_to_display)
        if article_url:
            st.write(f"[Source Link]({article_url})")
        st.divider()
else:
    # This acts as the clean catch-all layout if data is an empty list
    st.warning("Waiting for local Z13 to push data to the archive...")

st.sidebar.divider()
if st.sidebar.button("Clear Cache"):
    st.cache_data.clear()