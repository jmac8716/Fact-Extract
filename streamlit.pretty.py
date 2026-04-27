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
    """, unsafe_allow_html=True) # <--- Correct parameter name

# This tells the cloud to look in the NewsArchive folder inside your GitHub repo
archive_folder = "NewsArchive"

# --- DATA ENGINE ---
def load_data():
    # Use relative path for GitHub/Streamlit Cloud
    archive_path = "./NewsArchive"
    
    if not os.path.exists(archive_path):
        return []
        
    files = glob.glob(os.path.join(archive_path, "*.json"))
    # 1. SORT HERE: Reverse alphabetical puts the newest timestamp first
    files.sort(reverse=True)
    # Filter out any non-string values just in case
    return [f for f in files if f is not None]

all_files = load_data()

# --- SIDEBAR ---
st.sidebar.title("Fact Archive")

# Filter the list to ensure no None values crept in
valid_files = [f for f in all_files if f and isinstance(f, str)]

if valid_files:
    # SORTING: Since your files are named like 20260426-2100.json, 
    # we can just sort the names alphabetically in reverse! 
    # It's faster and won't crash like os.path.getmtime.
    valid_files.sort(reverse=True)
    
    # Create the display names
    file_display_names = [os.path.basename(f) for f in valid_files]
    
    selected_name = st.sidebar.selectbox("Choose Report Time:", file_display_names, index=0)
    
    # Use the name to build the full path
    file_path = os.path.join("NewsArchive", selected_name)
else:
    st.sidebar.warning("No archives found. Check your GitHub 'NewsArchive' folder.")
    file_path = None

# --- MAIN DASHBOARD ---
st.title("Fact Extract - 100% Concentrate")
st.divider()

if file_path:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Top level metrics
    m1, m2 = st.columns(2)
    if data:
        m1.metric("Current Articles", len(data))
        unique_cats = len(set(entry.get('category', 'Unknown') for entry in data))
        m2.metric("Categories", unique_cats)
    else:    
        st.warning("No data found in this report.")

    st.write("---")

# --- MAIN DISPLAY AREA ---

# This is the 'if' line you need to add back:
if data:
    for entry in data:
        # 1. Get the title from JSON
        category = entry.get('category', 'GENERAL').upper # Fallback to 'General' if missing
        saved_title = entry.get('title')
        article_url = entry.get('url', '')
        

        # 2. Logic Switch: If title exists and isn't just a link, use it.
        # Otherwise, fall back to cleaning the URL.
        if saved_title and "http" not in saved_title:
            display_title = saved_title
        
        else:
            # Fallback: Clean the URL slug
            raw_slug = article_url.split('/')[-1].split('?')[0]
            display_title = raw_slug.replace(".html", "").replace("-", " ").replace("_", " ").title()
        
        # A. Category first (Small and subtle, or bold)
        st.markdown(f":blue[**{category}**]")
        
        # 3. Display the clean title
        st.subheader(f"{display_title}")
    
        # 4. Display the content
        content_to_display = entry.get('report', entry.get('facts', "No content available"))
        st.markdown(content_to_display)
        st.write(f"[Source Link]({article_url})") # Optional: adds a clickable link
        st.divider()

else:
    st.warning("Waiting for local Z13 to push data to the archive...")

st.sidebar.divider()
if st.sidebar.button("Clear Cache"):
    st.cache_data.clear()