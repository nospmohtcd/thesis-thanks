import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. APP CONFIG & STYLING ---
st.set_page_config(page_title="Thesis Thanks", page_icon="🎓", layout="centered")

# Custom CSS for a clean academic look
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .tribute-card { 
        padding: 2rem; 
        border-radius: 10px; 
        border-left: 5px solid #0e1117;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE CONNECTION ---
# This uses the Service Account defined in your Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        return conn.read(ttl="10s")
    except Exception:
        # Returns empty structure if sheet is brand new/empty
        return pd.DataFrame(columns=["author", "title", "content", "reference_url"])

# --- 3. ROUTER LOGIC (Unique Link Viewer) ---
query_params = st.query_params
BASE_URL = "https://thesis-thanks.streamlit.app/"

if "id" in query_params:
    entry_id = query_params["id"]
    df = get_data()
    
    try:
        # Pull specific row based on index
        tribute = df.iloc[int(entry_id)]
        
        st.markdown(f"### 🎓 A Tribute by **{tribute['author']}**")
        st.divider()
        
        # Display the Tribute
        st.markdown(f"## {tribute['title']}")
        st.info(tribute['content'])
        
        if tribute['reference_url']:
            st.link_button("📄 View Original Thesis", tribute['reference_url'])
        
        st.divider()
        if st.button("⬅️ Create Your Own Tribute"):
            st.query_params.clear()
            st.rerun()
        
        st.stop() # Prevents the rest of the app from loading
        
    except (IndexError, ValueError):
        st.error("Tribute not found. It may have been moved or deleted.")
        if st.button("Back to Home"):
            st.query_params.clear()
            st.rerun()

# --- 4. MAIN APP (Writer & Gallery Mode) ---
st.title("🎓 Thesis Thanks")
st.write("Turn your thesis acknowledgments into a permanent, shareable tribute.")

tabs = st.tabs(["✍️ Write a Tribute", "🖼️ The Gallery"])

# TAB 1: SUBMISSION FORM
with tabs[0]:
    with st.form("tribute_form", clear_on_submit=True):
        st.subheader("Your Thesis Details")
        author = st.text_input("Your Name", placeholder="e.g., John Nash")
        thesis_title = st.text_input("Thesis Title", placeholder="e.g., Non-Cooperative Games")
        
        st.subheader("The Acknowledgments")
        content = st.text_area("Copy your 'Thanks' section here...", height=200)
        
        ref_url = st.text_input("Link to Thesis (URL or DOI)", placeholder="https://...")
        
        submitted = st.form_submit_button("💾 Save to Cloud & Generate Link")
        
        if submitted:
            if author and content and thesis_title:
                df = get_data()
                next_id = len(df)
                
                new_entry = pd.DataFrame([{
                    "author": str(author),
                    "title": str(thesis_title),
                    "content": str(content),
                    "reference_url": str(ref_url)
                }])
                
                updated_df = pd.concat([df, new_entry], ignore_index=True)
                conn.update(data=updated_df)
                
                # Show the Unique Link
                unique_url = f"{BASE_URL}?id={next_id}"
                st.success("Tribute Saved!")
                st.markdown("#### 🔗 Share this specific tribute:")
                st.code(unique_url)
                st.balloons()
            else:
                st.error("Please fill in your Name, Title, and the Thanks content.")

# TAB 2: THE GALLERY
with tabs[1]:
    df = get_data()
    if df.empty:
        st.write("The gallery is empty. Be the first to add a tribute!")
    else:
        for index, row in df.iterrows():
            with st.expander(f"🎓 {row['author']} — {row['title'][:50]}..."):
                st.write(row['content'])
                st.markdown(f"[View Individual Page]({BASE_URL}?id={index})")
