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

archive_folder = "C:\Users\jmac8\OneDrive\Documents\GitHub\Fact Extract\NewsArchive"

# --- DATA ENGINE ---
def load_data():
    # Use relative path for GitHub/Streamlit Cloud
    archive_path = "./NewsArchive"
    
    if not os.path.exists(archive_path):
        return []
        
    files = glob.glob(os.path.join(archive_path, "*.json"))
    # Filter out any non-string values just in case
    return [f for f in files if f is not None]

all_files = load_data()

# --- SIDEBAR ---
st.sidebar.title("Fact Archive")

# Ensure all_files is a list and has content
if all_files and len(all_files) > 0:
    # Sort by time so newest is on top
    all_files.sort(key=os.path.getmtime, reverse=True)
    
    # Create the display names safely
    file_display_names = [os.path.basename(f) for f in all_files if f]
    
    selected_name = st.sidebar.selectbox("Choose Report Time:", file_display_names)
    file_path = os.path.join("./NewsArchive", selected_name)
else:
    st.sidebar.warning("No archives found. Check your GitHub 'NewsArchive' folder.")
    file_path = None# --- MAIN DASHBOARD ---
st.title("Fact Extract - 100% Concentrate")
st.markdown(f"**Hardware Instance:** ROG Flow Z13 (128GB) | **Core Engine:** Llama 3.1 70B")
st.divider()

if file_path:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Top level metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Current Articles", len(data))
    m2.metric("Security Status", "Secured")
    m3.metric("Local Compute", "GPU Enabled")

    st.write("---")

    for entry in data:
        # Create a professional container for each article
        with st.container():
            # Header Columns
            head_col, link_col = st.columns([5, 1])
            with head_col:
                st.subheader(f"🌐 Analysis: {entry['url'].split('/')[-1][:50]}...")
            with link_col:
                st.link_button("Open Source", entry['url'])
            
            # The Content
            content_to_display = entry.get('report', entry.get('facts', "No content available"))
            st.markdown(content_to_display)
            
            # The Footer (Fixed Indentation here)
            st.caption(f"Processed at {entry.get('time', 'N/A')} | System: Q8_0 Local Quantization")
            st.divider()

else:
    st.warning("Waiting for local Z13 to push data to the archive...")

st.sidebar.divider()
if st.sidebar.button("Clear Cache"):
    st.cache_data.clear()