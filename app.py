import streamlit as st
from streamlit_gsheets import GSheetsConnection
import requests
import pandas as pd
import urllib.parse
import re

# --- 1. THE ENGINE (Google Sheets Version) ---

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_all_thanks():
    # Read existing data from the sheet
    return conn.read(ttl="10s") # ttl=10s ensures we see new entries quickly

def save_to_sheets(author, title, content, ref_url, tags):
    # 1. Fetch existing data
    existing_data = conn.read()
    
    # 2. Create the new row
    new_entry = pd.DataFrame([{
        "author": author,
        "title": title,
        "content": content,
        "reference_url": ref_url,
        "tags": tags
    }])
    
    # 3. Combine and Update
    updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
    conn.update(data=updated_df)

# --- 2. METADATA & PARSING (Remains the same) ---

def get_doi_metadata(doi):
    doi = doi.replace("https://doi.org/", "").strip()
    try:
        resp = requests.get(f"https://api.crossref.org/works/{doi}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()['message']
            title = data.get('title', [""])[0]
            authors = ", ".join([f"{a.get('given')} {a.get('family')}" for a in data.get('author', [])])
            return title, authors
    except: return None, None

def parse_citation_string(citation):
    author, title = "", ""
    parts = re.split(r'\(\d{4}\)', citation)
    if len(parts) >= 2:
        author = parts[0].strip().strip('.')
        title_part = parts[1].split('.')
        title = title_part[1].strip() if len(title_part) > 1 else title_part[0].strip()
    else:
        parts = citation.split('.', 2)
        if len(parts) >= 2:
            author, title = parts[0].strip(), parts[1].strip()
    return title, author

# --- 3. SETUP & STYLING ---

st.set_page_config(page_title="Thesis Thanks", page_icon="🎓")

st.markdown("""
    <style>
    div[data-baseweb="radio"] div div:nth-child(2) { background-color: #007bff !important; }
    .stRadio > label { font-weight: bold; color: #2c3e50; }
    .tag-label {
        background-color: #e9ecef; color: #495057; padding: 2px 8px;
        border-radius: 12px; font-size: 0.8rem; margin-right: 5px;
        display: inline-block; border: 1px solid #dee2e6;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎓 Thesis Thanks")

# Intro Text
st.markdown("""
    <div style="background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 2rem;">
        <p style="font-style: italic; color: #34495e; font-size: 1.1rem; line-height: 1.6;">
            "You’ve done the hard work. You’ve finished the research, survived the write-up, and dedicated a page (or two) to the people who carried you through. 
            But unless they’re planning to hunt down your library deposit, they’ll likely never see it."
        </p>
        <p style="margin-top: 15px; font-size: 1.05rem;">
            <strong>Thesis Thanks changes that.</strong> Simply paste your acknowledgments below to create a shareable tribute.
        </p>
    </div>
""", unsafe_allow_html=True)

menu = st.sidebar.selectbox("Menu", ["Create New", "View Gallery"])
tag_options = ["Family", "Supervisor", "Colleagues", "Friends", "Participants", "Funding Body", "Emotional Support", "Technical Help"]

if menu == "Create New":
    st.header("1. Identify the Thesis")
    mode = st.radio("Choose how to identify your work:", ["DOI Shortcut", "Paste Full Citation", "Enter Manually / Link"], horizontal=True)

    final_author, final_title, final_ref = "", "", ""

    if mode == "DOI Shortcut":
        doi_in = st.text_input("Enter DOI")
        if st.button("Fetch from DOI"):
            t, a = get_doi_metadata(doi_in)
            if t: st.session_state['t_title'], st.session_state['t_author'] = t, a
        final_author = st.text_input("Author Name", value=st.session_state.get('t_author', ""))
        final_title = st.text_input("Thesis Title", value=st.session_state.get('t_title', ""))
        final_ref = f"https://doi.org/{doi_in}" if doi_in else ""

    elif mode == "Paste Full Citation":
        cit_in = st.text_area("Paste Citation")
        if st.button("Parse Citation"):
            t, a = parse_citation_string(cit_in)
            if t: st.session_state['t_title'], st.session_state['t_author'] = t, a
        final_author = st.text_input("Author Name", value=st.session_state.get('t_author', ""))
        final_title = st.text_input("Thesis Title", value=st.session_state.get('t_title', ""))
        final_ref = st.text_input("Link (Optional)")

    elif mode == "Enter Manually / Link":
        final_author = st.text_input("Author Name")
        final_title = st.text_input("Thesis Title")
        final_ref = st.text_input("Thesis Link")

    st.markdown("---")
    st.header("2. Write your Acknowledgments")
    thanks_text = st.text_area("Your Acknowledgments", height=300)
    selected_tags = st.multiselect("Who are you thanking?", tag_options)
    tags_string = ", ".join(selected_tags)

    if st.button("💾 Save to Cloud"):
        if final_author and thanks_text:
            with st.spinner("Writing to Google Sheets..."):
                save_to_sheets(final_author, final_title, thanks_text, final_ref, tags_string)
            st.success("Tribute saved to the cloud!")
            st.balloons()
        else:
            st.error("Author and Acknowledgments are required.")

else:
    st.header("📜 Saved Acknowledgments")
    df = get_all_thanks()
    
    if df.empty:
        st.info("The gallery is empty.")
    else:
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search_query = st.text_input("🔍 Search", placeholder="Search...")
        with col_filter:
            filter_tag = st.selectbox("Category", ["All"] + tag_options)

        # Convert DF to list of dicts for easy looping
        rows = df.to_dict('records')
        
        for item in rows:
            # Handle potential NaN values from Sheets
            author = str(item.get('author', ''))
            title = str(item.get('title', ''))
            content = str(item.get('content', ''))
            tags = str(item.get('tags', ''))
            ref = str(item.get('reference_url', ''))

            searchable = f"{author} {title} {content}".lower()
            if (search_query.lower() in searchable) and (filter_tag == "All" or filter_tag in tags):
                with st.expander(f"📄 {title} — {author}"):
                    if tags:
                        tag_html = "".join([f'<span class="tag-label">{t.strip()}</span>' for t in tags.split(",")])
                        st.markdown(tag_html, unsafe_allow_html=True)
                    st.write(content)
                    if ref: st.markdown(f"🔗 **Ref:** [{ref}]({ref})")
                    st.divider()
                    
                    # Sharing Section
                    emails = st.text_input("Recipient Emails", key=f"em_{author[:5]}")
                    perma_link = "https://thesisthanks.com" # Placeholder for your future domain
                    
                    subject = urllib.parse.quote(f"Acknowledgments from {author}")
                    body = urllib.parse.quote(f"Check this out:\n\n{content}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f'<a href="mailto:{emails}?subject={subject}&body={body}"><button style="width:100%; cursor:pointer; background:#007bff; color:white; border:none; padding:10px; border-radius:5px;">📧 Open Email</button></a>', unsafe_allow_html=True)
                    with c2:
                        st.code(perma_link, language=None)
