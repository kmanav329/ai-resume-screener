import streamlit as st
import json
import requests  # <--- NEW LIBRARY
from openai import OpenAI
from pypdf import PdfReader
from fpdf import FPDF

# 1. Page Config
st.set_page_config(page_title="AI Resume Optimizer", page_icon="🚀", layout="wide")

# 2. API Key
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("API Key missing!")
    st.stop()

client = OpenAI(api_key=api_key)

# --- HELPER FUNCTIONS ---

def fetch_jd_from_url(url):
    """
    Fetches text from a URL using Jina Reader (LLM-friendly scraper).
    """
    try:
        # Jina Reader turns any website into clean Markdown for AI
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, timeout=10)
        return response.text
    except Exception as e:
        return None

def get_analysis(resume_txt, jd_txt):
    """
    Analyzes the fit between resume and JD using STRICT criteria.
    """
    prompt = f"""
    Act as a ruthlessly efficient Applicant Tracking System (ATS).
    Compare the RESUME vs JOB DESCRIPTION.
    
    SCORING RULES:
    - 100%: Perfect match (Hard skills, years of exp, specific tools).
    - <60%: Missing critical keywords.
    
    CRITICAL: Ignore "Soft Skills". Focus ONLY on Hard Skills.

    Return strictly JSON:
    {{
        "match_percentage": Integer (0-100),
        "missing_keywords": List[String],
        "summary": String
    }}
    
    JOB DESCRIPTION: {jd_txt[:5000]}
    RESUME: {resume_txt[:5000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def generate_improved_content(resume_txt, jd_txt):
    """
    Rewrites using Google XYZ Formula.
    """
    prompt = f"""
    You are a Top-Tier Resume Writer. 
    Rewrite the RESUME to target the JOB DESCRIPTION.
    
    Use the Google XYZ formula: "Accomplished [X] as measured by [Y], by doing [Z]".
    
    Output Format (Plain Text):
    PROFESSIONAL SUMMARY
    [Text]
    TECHNICAL SKILLS
    [Text]
    PROFESSIONAL EXPERIENCE
    [Role] | [Company] | [Dates]
    - [XYZ Bullet]
    EDUCATION
    [Text]
    
    JOB DESCRIPTION: {jd_txt[:5000]}
    RESUME: {resume_txt[:5000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)
    safe_text = text.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 10, safe_text)
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN UI ---

st.title("🚀 AI Resume Optimizer")
st.markdown("Upload your resume and provide a Job Description (Text or Link).")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. The Job")
    # Tabs for Text vs Link
    jd_tab1, jd_tab2 = st.tabs(["Paste Text", "Paste Link (LinkedIn/Indeed)"])
    
    with jd_tab1:
        jd_text_input = st.text_area("Paste JD Text", height=200)
    
    with jd_tab2:
        jd_url = st.text_input("Paste Job Posting URL")
        if jd_url:
            with st.spinner("Fetching Job Description..."):
                fetched_jd = fetch_jd_from_url(jd_url)
                if fetched_jd:
                    st.success("✅ Job Description Loaded!")
                    with st.expander("View Fetched Content"):
                        st.text(fetched_jd[:500]) # Preview
                else:
                    st.error("Could not fetch URL. Please copy-paste the text instead.")

with col2:
    st.subheader("2. Your Resume")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if st.button("Optimize Resume"):
    # 1. Determine which JD to use
    final_jd = None
    if jd_text_input:
        final_jd = jd_text_input
    elif jd_url and fetched_jd:
        final_jd = fetched_jd
        
    if not final_jd or not uploaded_file:
        st.warning("Please provide a Job Description (Text or Link) AND a Resume.")
    else:
        # 2. Read PDF
        with st.spinner("Reading resume..."):
            reader = PdfReader(uploaded_file)
            original_text = ""
            for page in reader.pages:
                original_text += page.extract_text() + "\n"

        # 3. Analyze
        with st.spinner("Analyzing fit..."):
            original_analysis = get_analysis(original_text, final_jd)

        # 4. Rewrite
        with st.spinner("Rewriting with XYZ Formula..."):
            improved_text = generate_improved_content(original_text, final_jd)

        # 5. Re-Analyze
        with st.spinner("Rescoring..."):
            new_analysis = get_analysis(improved_text, final_jd)

        # 6. PDF
        pdf_data = create_pdf(improved_text)

        # --- RESULTS ---
        st.divider()
        st.subheader("📊 Results")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Original Score", f"{original_analysis['match_percentage']}%")
        with c2:
            st.metric("Optimized Score", f"{new_analysis['match_percentage']}%")
        with c3:
            imp = new_analysis['match_percentage'] - original_analysis['match_percentage']
            st.metric("Improvement", f"+{imp}%")

        st.write("### 🔍 Gap Analysis")
        col_a, col_b = st.columns(2)
        with col_a:
            st.info(f"**Missing Keywords:** {', '.join(original_analysis['missing_keywords'])}")
            st.write(f"**Critique:** {original_analysis['summary']}")
        with col_b:
            st.success(f"**Optimization:** {new_analysis['summary']}")
            
        st.divider()
        st.subheader("📥 Download")
        st.download_button("Download Optimized PDF", pdf_data, "Optimized_Resume.pdf", "application/pdf")
