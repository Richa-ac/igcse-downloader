import streamlit as st
import requests
import io
import time
import pikepdf
import os 
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="IGCSE PastPaper Downloader", layout="centered")

hide_st_style = """
            <style>
            /* Hides the top header bar and the red crown */
            [data-testid="stHeader"] {display: none !important;}
            
            /* Hides the 'Made with Streamlit' footer */
            footer {visibility: hidden !important;}
            
            /* Hides the hamburger menu (top right) */
            #MainMenu {visibility: hidden !important;}
            
            /* Removes extra padding at the top so your H1 is snug */
            .block-container {padding-top: 0rem !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

SUBJECTS = {
    "0625 Physics": {"code":"0625","papers":[2,4,6]},
    "0620 Chemistry": {"code":"0620","papers":[2,4,6]},
    "0610 Biology": {"code":"0610","papers":[2,4,6]},
    "0478 Computer Science": {"code":"0478","papers":[1,2]},
    "0500 English": {"code":"0500","papers":[1,2]},
    "0580 Mathematics": {"code":"0580","papers":[2,4]},
    "0417 ICT": {"code":"0417","papers":[1]},
    "0450 Business Studies": {"code":"0450","papers":[1,2]},
    "0455 Economics": {"code":"0455","papers":[1,2]},
    "0471 Travel & Tourism": {"code":"0471","papers":[1,2]},
    "0680 Environmental Management": {"code":"0680","papers":[1,2]},
    "0452 Accounting": {"code":"0452","papers":[1,2]},
    "0470 History": {"code":"0470","papers":[1,2,4]},
    "0495 Sociology": {"code":"0495","papers":[1,2]},
}

SUBJECT_COLORS = {
    "0625 Physics": "#2563eb", "0620 Chemistry": "#059669", "0610 Biology": "#db2777",
    "0478 Computer Science": "#7c3aed", "0500 English": "#ea580c", "0580 Mathematics": "#06b6d4",
    "0417 ICT": "#0ea5e9", "0450 Business Studies": "#84cc16", "0455 Economics": "#f59e0b",
    "0471 Travel & Tourism": "#0891b2", "0680 Environmental Management": "#15803d",
    "0452 Accounting": "#6366f1", "0470 History": "#b91c1c", "0495 Sociology": "#d946ef",
    "Default": "#e11d48"
}

KNOWN_MISSING = [
    "0452_w25_qp_11.pdf", "0452_w25_ms_11.pdf",
    "0452_w25_qp_21.pdf", "0452_w25_ms_21.pdf",
    "0470_s18_qp_13.pdf", "0470_s18_ms_13.pdf",
    "0470_w20_qp_42.pdf", "0470_w20_ms_42.pdf"
]

BASE_URL = "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/"
RESCUE_DIR = "rescued_papers"
if not os.path.exists(RESCUE_DIR): os.makedirs(RESCUE_DIR)

http = requests.Session()

st.markdown("<h1>Past Paper Downloader</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-weight: 500;'>Get your papers and mark schemes in one single PDF</p>", unsafe_allow_html=True)


# --- SELECTION ---
st.markdown("<span class='section-label'>Subject Selection</span>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    subject = st.selectbox("Pick a subject", list(SUBJECTS.keys()), on_change=lambda: st.session_state.pop('final_pdf', None))
    code = SUBJECTS[subject]["code"]
with col2:
    paper = st.selectbox("Paper number", SUBJECTS[subject]["papers"], on_change=lambda: st.session_state.pop('final_pdf', None))
   
active_color = SUBJECT_COLORS.get(subject, SUBJECT_COLORS["Default"])

st.markdown(f"""
<style>
    .stAppViewContainer {{ background-image: linear-gradient(135deg, transparent 0%, {active_color}20 100%) !important; transition: all 0.6s ease-in-out !important; }}
    h1 {{ color: {active_color} !important; font-weight: 800 !important; font-size: 3.2rem !important; text-align: center; margin-bottom: 10px !important; }}
    .section-label {{ color: {active_color} !important; background: {active_color}20; padding: 4px 12px; border-radius: 8px; font-weight: 800; display: inline-block; margin-bottom: 10px; }}
    .stButton>button {{ background-color: {active_color} !important; color: white !important; height: 3.5em; width: 100%; font-weight: 700; border-radius: 12px; box-shadow: 0 8px 15px {active_color}40 !important; }}
    .footer-pill {{
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(5px);
        padding: 6px 20px;
        border-radius: 20px;
        border: 1px solid {active_color}30;
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 500;
        z-index: 999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .footer-pill b {{
        color: {active_color};
    }}
</style>
<div class="footer-pill">Developed by <b>Richa Choudhary</b></div>
""", unsafe_allow_html=True)

# --- FLOATING SUPPORT BUBBLE ---
st.markdown(f"""
    <style>
    /* The hidden checkbox that controls the bubble */
    #support-toggle {{ display: none; }}

    /* The floating circle button */
    .floating-button {{
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 60px;
        height: 60px;
        background-color: {active_color};
        color: white !important;
        border-radius: 50px;
        text-align: center;
        box-shadow: 2px 5px 15px rgba(0,0,0,0.3);
        z-index: 1001;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 24px;
        transition: transform 0.3s ease;
    }}

    /* The Text Bubble */
    .support-bubble {{
        position: fixed;
        bottom: 100px;
        right: 30px;
        width: 250px;
        padding: 15px;
        background-color: white;
        color: #1e293b;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        z-index: 1000;
        font-size: 14px;
        display: none; /* Hidden by default */
        border: 1px solid #e2e8f0;
    }}

    /* Show the bubble when the button is clicked (checkbox is checked) */
    #support-toggle:checked ~ .support-bubble {{
        display: block;
    }}

    /* Pointer triangle for the bubble */
    .support-bubble::after {{
        content: '';
        position: absolute;
        bottom: -10px;
        right: 20px;
        border-left: 10px solid transparent;
        border-right: 10px solid transparent;
        border-top: 10px solid white;
    }}
    </style>

    <input type="checkbox" id="support-toggle">
    <label for="support-toggle" class="floating-button">📩</label>
    
    <div class="support-bubble">
        <b>Facing errors?</b><br>
        Drop a message at <b>richa121611@gmail.com</b> with a screenshot and description of your error!
    </div>
""", unsafe_allow_html=True)

    # --- INPUTS & LOGIC ---
doc_choice = st.radio("Document Type", ["Question Paper", "Mark Scheme"], horizontal=True, on_change=lambda: st.session_state.pop('final_pdf', None))
type_code = "qp" if doc_choice == "Question Paper" else "ms"

st.markdown("<br><span class='section-label'>Year & Session</span>", unsafe_allow_html=True)
s1, s2, s3 = st.columns(3)
sessions = []
with s1: 
    if st.checkbox("Feb/March"): sessions.append("m")
with s2: 
    if st.checkbox("May/June"): sessions.append("s")
with s3: 
    if st.checkbox("Oct/Nov"): sessions.append("w")
    
if "m" in sessions and code in ["0495","0471"]:
    st.warning(f"Feb/March Sessions do not exist for {subject}. These will be skipped.")

start_year, end_year = st.slider("Select Year Range", 2018, 2025, (2018, 2025), on_change=lambda: st.session_state.pop('final_pdf', None))

variants = []
v1, v2, v3 = st.columns(3)
with v1: 
    if st.checkbox("Variant 1", value=True): variants.append("1")
with v2: 
    if st.checkbox("Variant 2"): variants.append("2")
with v3: 
    if st.checkbox("Variant 3"): variants.append("3")

def get_pdf(filename):
    local_path = os.path.join(RESCUE_DIR, filename)
    if os.path.exists(local_path):
        with open(local_path, "rb") as f: return filename, f.read()
    try:
        r = http.get(BASE_URL + filename, timeout=5)
        if r.status_code == 200 and len(r.content) > 10000:
            return filename, r.content
    except:     pass
    return filename, None

st.markdown("<br>", unsafe_allow_html=True)

button_placeholder = st.empty()
if st.button("Compile Papers"):
    st.session_state.pop('final_pdf', None)
    st.session_state.pop('missing_list', None)
    start_time = time.perf_counter()
    if not sessions:
        st.warning("Please pick a session first!")
        st.stop()
        
    targets = []
    for yr in range(start_year, end_year + 1):
        y = str(yr)[-2:]
        for sess in sessions:
            if sess == "m" and code in ["0495","0471"]:
                continue
            if sess == "m":
                if "2" in variants:
                    targets.append(f"{code}_{sess}{y}_{type_code}_{paper}2.pdf")
            else:
                for v in variants:
                    targets.append(f"{code}_{sess}{y}_{type_code}_{paper}{v}.pdf")
    missing_ones=[f for f in targets if f in KNOWN_MISSING]
    targets = [f for f in targets if f not in KNOWN_MISSING]      
    
    downloaded = {}
  
    with st.status("Downloading papers...just a moment", expanded=True) as status:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(get_pdf, f): f for f in targets}
            for future in as_completed(futures):
                fname, content = future.result()
                if content:
                    try: 
                        parts = fname.split('_')
                        if len(parts) > 1 and len(parts[1]) >= 3:
                            year_part = parts[1][1:3] # Explicitly get the YY
                            sort_key = f"{year_part}_{fname}"
                        else:
                            sort_key = f"99_{fname}" # Fallback to end of PDF
                    except Exception:
                        sort_key = fname
                    downloaded[sort_key] = content
                else:
                    missing_ones.append(fname)
        if not downloaded:
            status.update(label="No papers found for this selection.", state="error")
            st.stop()

        pdf_out = pikepdf.Pdf.new()
        # Sorted by filename so the years follow a logical order in the PDF
        for fn in sorted(downloaded.keys()):
            try:
                with pikepdf.open(io.BytesIO(downloaded[fn])) as src:
                    pdf_out.pages.extend(src.pages)
            except: continue
            
        buf = io.BytesIO()
        pdf_out.save(buf)
        st.session_state['final_pdf'] = buf.getvalue()
        st.session_state['real count'] = len(downloaded)
        st.session_state['missing_list'] = missing_ones

        end_time = time.perf_counter()
        duration = end_time - start_time
        st.toast(f"🚀 Compiled {len(downloaded)} papers in {duration:.2f}s", icon="⚡")

if 'final_pdf' in st.session_state:
    st.success(f"✅ Success! {st.session_state['real count']} papers compiled.")
    if st.session_state.get('missing_list'):
        non_existent = [f for f in st.session_state['missing_list'] if f in KNOWN_MISSING]
        server_errors = [f for f in st.session_state['missing_list'] if f not in KNOWN_MISSING]
        with st.expander(f"{len(st.session_state['missing_list'])} Papers Skipped/Missing"):
            if non_existent:
                st.markdown("**Non-existent papers (not released by CAIE):**")
                for f in sorted(st.session_state['missing_list']):
                    st.write(f"🚫 {f}")
            if non_existent and server_errors: st.divider()

            # 2. Show the potential server errors
            if server_errors:
                st.markdown("**Papers not found (try refreshing the site!):**")
                for f in sorted(server_errors):
                    st.write(f"🔄 {f}")
    
    generated_filename = f"{code}_p{paper}_{start_year}-{end_year}_{type_code}.pdf"
    
    st.download_button(
    label=f"Download Paper {paper} {doc_choice}s", 
    data=st.session_state['final_pdf'], 
    file_name=generated_filename, 
    use_container_width=True)