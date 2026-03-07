import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
import re

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="Thesis Thanks", page_icon="🎓", layout="centered")
BASE_URL = "https://thesis-thanks.streamlit.app/"

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, p, span, div { color: #1A1A1A !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC FUNCTIONS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_doi_metadata(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()['message']
            title = data.get('title', [''])[0]
            author_list = data.get('author', [])
            author_name = f"{author_list[0].get('given', '')} {author_list[0].get('family', '')}" if author_list else "Unknown"
            return author_name, title
    except: return None, None
    return None, None

def parse_citation(citation):
    """Simple parser to extract Author and Title from a standard citation string"""
    # Attempt to find Author (usually before the first period or year)
    author_match = re.search(r'^([^,(]+)', citation)
    # Attempt to find Title (usually inside quotes or between dates and journal)
    title_match = re.search(r'[“"‘\'](.+?)[”"’\']|(?<=\d\)\.\s)(.+?)(?=\.)', citation)
    
    author = author_match.group(0).strip() if author_match else "Unknown Author"
    title = title_match.group(0).strip(" .\"'“”‘’") if title_match else "Unknown Title"
    return author, title

def get_data():
    try: return conn.read(ttl="0")
    except: return pd.DataFrame(columns=["author", "title", "content", "reference_url"])

# --- 3. ROUTER (Unique Link View) ---
query_params = st.query_params
if "id" in query_params:
    entry_id = query_params["id"]
    df = get_data()
    try:
        tribute = df.iloc[int(entry_id)]
        st.markdown(f"### 🎓 A Tribute by **{tribute['author']}**")
        st.divider()
        st.title(tribute['title'])
        st.info(tribute['content'])
        if tribute['reference_url'] and str(tribute['reference_url']) != "nan":
            st.link_button("📄 View Thesis", tribute['reference_url'])
        if st.button("⬅️ Back Home"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    except: st.error("Entry not found."); st.stop()

# --- 4. MAIN APP ---
st.title("🎓 Thesis Thanks")
tabs = st.tabs(["✍️ Submit Your Thanks", "🖼️ Gallery"])

with tabs[0]:
    # THE RADIO BUTTONS
    mode = st.radio("Choose Input Method", ["Manual", "DOI", "Paste Citation"], horizontal=True)
    
    with st.form("entry_form", clear_on_submit=True):
        author_val, title_val = "", ""
        
        if mode == "DOI":
            doi_in = st.text_input("Enter DOI")
            if st.form_submit_button("🔍 Fetch"):
                a, t = get_doi_metadata(doi_in)
                if a: 
                    st.session_state.a, st.session_state.t = a, t
                    st.success(f"Found: {a}")
                else: st.error("DOI not found")
            author_val = st.session_state.get('a', "")
            title_val = st.session_state.get('t', "")

        elif mode == "Paste Citation":
            cite_in = st.text_area("Paste APA/MLA/Chicago Citation")
            if st.form_submit_button("🛠️ Parse"):
                a, t = parse_citation(cite_in)
                st.session_state.a, st.session_state.t = a, t
                st.success(f"Extracted: {a}")
            author_val = st.session_state.get('a', "")
            title_val = st.session_state.get('t', "")

        else: # Manual
            author_val = st.text_input("Author Name")
            title_val = st.text_input("Thesis Title")

        # Core fields
        final_author = st.text_input("Final Author Name", value=author_val)
        final_title = st.text_input("Final Thesis Title", value=title_val)
        thanks_text = st.text_area("Acknowledgments Content", height=200)
        thesis_url = st.text_input("Thesis Link (Optional)")

        if st.form_submit_button("💾 Save & Generate Link"):
            if final_author and thanks_text:
                df = get_data()
                new_idx = len(df)
                new_row = pd.DataFrame([{"author": final_author, "title": final_title, "content": thanks_text, "reference_url": thesis_url}])
                conn.update(data=pd.concat([df, new_row], ignore_index=True))
                
                st.success("Tribute Saved!")
                st.code(f"{BASE_URL}?id={new_idx}")
                st.balloons()
            else: st.warning("Author and Content are required.")

with tabs[1]:
    df = get_data()
    if not df.empty:
        for i, row in df.iterrows():
            with st.expander(f"🎓 {row['author']} - {str(row['title'])[:40]}..."):
                st.write(row['content'])
                st.markdown(f"[View Page]({BASE_URL}?id={i})")
