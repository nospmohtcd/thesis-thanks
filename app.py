import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="Thesis Thanks", page_icon="🎓", layout="centered")
BASE_URL = "https://thesis-thanks.streamlit.app/"

# High-contrast CSS
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, p, span, div { color: #1A1A1A !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE & DOI LOGIC ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_doi_metadata(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=5)
        if response.status_status == 200:
            data = response.json()['message']
            title = data.get('title', [''])[0]
            # Authors usually come in a list
            author_list = data.get('author', [])
            author_name = f"{author_list[0].get('given', '')} {author_list[0].get('family', '')}" if author_list else ""
            return author_name, title
    except:
        return None, None
    return None, None

def get_data():
    try:
        return conn.read(ttl="0")
    except:
        return pd.DataFrame(columns=["author", "title", "content", "reference_url"])

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
        st.divider()
        if st.button("⬅️ Create Your Own"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    except:
        st.error("Entry not found.")
        st.stop()

# --- 4. MAIN APP ---
st.title("🎓 Thesis Thanks")
tabs = st.tabs(["✍️ Submit", "🖼️ Gallery"])

with tabs[0]:
    # --- THE RADIO BUTTONS ARE BACK ---
    input_method = st.radio("How would you like to start?", ["Fetch via DOI", "Manual Entry"], horizontal=True)
    
    with st.form("main_form", clear_on_submit=True):
        final_author = ""
        final_title = ""
        
        if input_method == "Fetch via DOI":
            doi_input = st.text_input("Enter Thesis DOI (e.g., 10.1038/nature12345)")
            if st.form_submit_button("🔍 Look up DOI"):
                author, title = get_doi_metadata(doi_input)
                if author:
                    st.success(f"Found: {title} by {author}")
                    # We store these in session state to persist them through the submit
                    st.session_state.doi_author = author
                    st.session_state.doi_title = title
                else:
                    st.error("Could not find DOI. Try manual entry.")
            
            final_author = st.session_state.get('doi_author', "")
            final_title = st.session_state.get('doi_title', "")
        else:
            final_author = st.text_input("Your Name")
            final_title = st.text_input("Thesis Title")

        thanks_text = st.text_area("Acknowledgments", height=250)
        ref_url = st.text_input("Thesis URL (Optional)")
        
        if st.form_submit_button("💾 Save & Generate Link"):
            if final_author and thanks_text:
                df = get_data()
                new_id = len(df)
                new_row = pd.DataFrame([{"author": final_author, "title": final_title, "content": thanks_text, "reference_url": ref_url}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success("Saved!")
                st.code(f"{BASE_URL}?id={new_id}")
                st.balloons()
            else:
                st.warning("Please ensure Name and Acknowledgments are filled.")

with tabs[1]:
    df = get_data()
    if not df.empty:
        for i, row in df.iterrows():
            with st.expander(f"🎓 {row['author']} - {row['title'][:40]}..."):
                st.write(row['content'])
                st.markdown(f"[View Page]({BASE_URL}?id={i})")
