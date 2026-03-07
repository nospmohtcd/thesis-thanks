import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
import re

# --- 1. APP CONFIG ---
st.set_page_config(page_title="Thesis Thanks", page_icon="🎓", layout="centered")
BASE_URL = "https://thesis-thanks.streamlit.app/"

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, p, span, div { color: #1A1A1A !important; }
    .intro-text { 
        font-size: 1.15rem; color: #333333 !important; line-height: 1.7; 
        background-color: #f9f9f9; padding: 20px; border-radius: 8px; border-left: 4px solid #0e1117;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HELPERS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try: return conn.read(ttl="0")
    except: return pd.DataFrame(columns=["author", "title", "content", "reference_url"])

def get_doi_metadata(doi):
    try:
        response = requests.get(f"https://api.crossref.org/works/{doi}", timeout=5)
        if response.status_code == 200:
            data = response.json()['message']
            title = data.get('title', [''])[0]
            authors = data.get('author', [])
            name = f"{authors[0].get('given', '')} {authors[0].get('family', '')}" if authors else "Unknown"
            return name, title
    except: return None, None
    return None, None

def parse_citation(citation):
    author = re.search(r'^([^,(]+)', citation)
    title = re.search(r'[“"‘\'](.+?)[”"’\']|(?<=\d\)\.\s)(.+?)(?=\.)', citation)
    return (author.group(0).strip() if author else ""), (title.group(0).strip(" .\"'") if title else "")

# --- 3. ROUTER ---
query_params = st.query_params
if "id" in query_params:
    entry_id = query_params["id"]
    df = get_data()
    try:
        tribute = df.iloc[int(entry_id)]
        st.markdown("### 🎓 A Thesis Tribute")
        st.divider()
        st.title(f"A Message from {tribute['author']}")
        st.subheader(f"Ref: {tribute['title']}")
        st.info(tribute['content'])
        if tribute['reference_url'] and str(tribute['reference_url']) != "nan":
            st.link_button("📄 View Original Thesis", tribute['reference_url'])
        st.divider()
        if st.button("⬅️ Create Your Own"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    except: st.error("Tribute not found."); st.stop()

# --- 4. LANDING PAGE ---
st.title("🎓 Thesis Thanks")

st.markdown("""
<div class="intro-text">
You’ve done the hard work. You’ve finished the research, survived the write-up, and dedicated a page (or two) to the people who carried you through. But unless they’re planning to hunt down your library deposit, they’ll likely never see it.
<br><br>
<b>Thesis Thanks</b> changes that. Simply paste your acknowledgments below to create a shareable tribute. Let them know that without them, this work wouldn't have seen the light of day.
</div>
""", unsafe_allow_html=True)

st.divider()

# Initialize session state for persistent fields
if 'author' not in st.session_state: st.session_state.author = ""
if 'title' not in st.session_state: st.session_state.title = ""

tabs = st.tabs(["✍️ Create Tribute", "🖼️ Gallery"])

with tabs[0]:
    mode = st.radio("Input Method", ["Manual", "DOI Lookup", "Citation Parser"], horizontal=True)
    
    # Logic for DOI/Citation runs OUTSIDE the main form to update session state
    if mode == "DOI Lookup":
        doi_in = st.text_input("Enter DOI")
        if st.button("🔍 Fetch DOI Data"):
            a, t = get_doi_metadata(doi_in)
            if a:
                st.session_state.author, st.session_state.title = a, t
                st.success("Data fetched!")
            else: st.error("DOI not found.")

    elif mode == "Citation Parser":
        cite_in = st.text_area("Paste Citation")
        if st.button("🛠️ Parse Citation"):
            a, t = parse_citation(cite_in)
            st.session_state.author, st.session_state.title = a, t
            st.success("Citation parsed!")

    # The Final Submission Form
    with st.form("tribute_form", clear_on_submit=True):
        # We use the session state as the default value
        final_author = st.text_input("Name", value=st.session_state.author)
        final_title = st.text_input("Thesis Title", value=st.session_state.title)
        thanks = st.text_area("Acknowledgments", height=250)
        link = st.text_input("Thesis Link (Optional)")
        
        submit_clicked = st.form_submit_button("🚀 Create Shareable Link")
        
        if submit_clicked:
            if final_author and thanks:
                df = get_data()
                new_id = len(df)
                new_row = pd.DataFrame([{"author": final_author, "title": final_title, "content": thanks, "reference_url": link}])
                conn.update(data=pd.concat([df, new_row], ignore_index=True))
                
                # Reset state after successful submit
                st.session_state.author = ""
                st.session_state.title = ""
                
                st.success("Tribute Created!")
                st.code(f"{BASE_URL}?id={new_id}")
                st.balloons()
            else:
                st.error("Name and Acknowledgments are required.")

with tabs[1]:
    df = get_data()
    if not df.empty:
        for i, row in df.iloc[::-1].iterrows():
            with st.expander(f"🎓 {row['author']} — {str(row['title'])[:50]}..."):
                st.write(row['content'])
                st.markdown(f"[View Full Page]({BASE_URL}?id={i})")
