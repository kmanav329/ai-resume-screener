import streamlit as st
import json
import os
import time
import io
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Load Config
load_dotenv()
st.set_page_config(page_title="Resume Architect AI", page_icon="🚀", layout="wide")

# 2. CSS for "Pro" Look
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #0070d2; color: white; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 3. API Setup
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    # Fallback for local testing if secrets not found
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("🚨 API Key Missing. Please check Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- HELPER FUNCTIONS ---

def simulate_processing():
    """UX Feature: Builds trust by showing 'Expert' steps."""
    my_bar = st.progress(0, text="Starting Analysis...")
    steps = [
        "📄 Parsing Resume Architecture...",
        "🔍 Extracting Hard Skills & Keywords...",
        "⚖️ Comparing against Job Description...",
        "📐 Applying 'Google XYZ' Success Formulas...",
        "✨ Formatting Professional Word Document..."
    ]
    for i, step in enumerate(steps):
        time.sleep(0.7)
        my_bar.progress((i + 1) * 20, text=step)
    time.sleep(0.5)
    my_bar.empty()

def create_docx(data):
    """Generates an Editable Word Doc from JSON."""
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # Header
    h1 = doc.add_paragraph()
    h1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = h1.add_run(data.get('name', 'Candidate Name'))
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = RGBColor(0, 112, 210) # Blue Header

    contact = doc.add_paragraph()
    contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contact.add_run(data.get('contact_info', 'Location | Email | Phone'))

    # Summary
    if data.get('summary'):
        doc.add_heading('PROFESSIONAL SUMMARY', level=1)
        doc.add_paragraph(data['summary'])

    # Skills
    if data.get('skills'):
        doc.add_heading('TECHNICAL SKILLS', level=1)
        # Handle if skills are a dict or list
        if isinstance(data['skills'], dict):
            for cat, items in data['skills'].items():
                p = doc.add_paragraph()
                p.add_run(f"{cat}: ").bold = True
                p.add_run(items)
        else:
             doc.add_paragraph(str(data['skills']))

    # Experience
    if data.get('experience'):
        doc.add_heading('PROFESSIONAL EXPERIENCE', level=1)
        for job in data['experience']:
            p = doc.add_paragraph()
            run = p.add_run(f"{job['role']} | {job['company']}")
            run.bold = True
            p.add_run(f"  ({job['dates']})").italic = True
            for bullet in job['bullets']:
                doc.add_paragraph(bullet, style='List Bullet')

    # Education
    if data.get('education'):
        doc.add_heading('EDUCATION', level=1)
        for edu in data['education']:
            doc.add_paragraph(f"{edu['degree']} - {edu['school']}")

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

def analyze_fit(resume_text, jd_text):
    """V2 PROMPT: Strict Scoring"""
    prompt = f"""
    Act as a Strict Technical Recruiter for a Fortune 500 company. 
    Analyze the RESUME against the JOB DESCRIPTION (JD).
    
    CRITERIA (Be Harsh):
    - Ignore "Soft Skills" (Leadership, Communication). Focus ONLY on Hard Skills (Tools, Languages, Frameworks).
    - Match Score depends on keyword density and context.

    Return strictly JSON:
    {{
        "match_percentage": Integer (0-100),
        "missing_keywords": ["List", "of", "missing", "hard", "skills"],
        "summary_critique": "1 sentence on why they pass or fail."
    }}
    
    JD: {jd_text[:3000]}
    RESUME: {resume_text[:3000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def rewrite_resume(resume_text, jd_text, gap_data):
    """V2 PROMPT: The 'Google XYZ' Formula (No Scraping Needed)"""
    prompt = f"""
    You are a Professional Resume Writer. Rewrite this resume to target the JD.
    
    CRITICAL INSTRUCTION:
    Use the 'Google XYZ Formula' for bullet points: "Accomplished [X] as measured by [Y], by doing [Z]".
    
    Example: 
    Bad: "Managed a team."
    Good: "Led a team of 10 (Z) to drive $2M in revenue (X), increasing sales by 15% YoY (Y)."

    INSTRUCTIONS:
    1. Integrate these missing skills: {gap_data['missing_keywords']}
    2. Quantify results where possible (estimate if needed based on context).
    3. Return valid JSON for a Word Document structure.

    Return JSON Structure:
    {{
        "name": "Name", "contact_info": "Contact",
        "summary": "Revised Summary",
        "skills": {{"Category": "List"}},
        "experience": [
            {{"role": "Title", "company": "Co", "dates": "Dates", "bullets": ["Star Method Bullet 1", "Star Method Bullet 2"]}}
        ],
        "education": [{{"degree": "Deg", "school": "Uni"}}]
    }}

    JD: {jd_text[:3000]}
    RESUME: {resume_text[:3000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o", # Smart model for writing
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- MAIN UI ---

st.title("🚀 Resume Architect AI")
st.markdown("Upload your resume and a JD. We will **Audit**, **Score**, and **Rewrite** it using the 'Google XYZ' formula.")

col1, col2 = st.columns(2)
with col1:
    jd_input = st.text_area("1️⃣ Paste Job Description", height=200)
with col2:
    uploaded_file = st.file_uploader("2️⃣ Upload Resume (PDF)", type="pdf")

if 'processed' not in st.session_state:
    st.session_state.processed = False

if st.button("🚀 Analyze & Rewrite"):
    if not jd_input or not uploaded_file:
        st.warning("⚠️ Please provide both inputs.")
    else:
        # UX: Simulate "Thinking"
        simulate_processing()
        
        # Read PDF
        reader = PdfReader(uploaded_file)
        text = "".join([page.extract_text() for page in reader.pages])
        
        # 1. Analyze
        with st.spinner("Calculating Score..."):
            analysis = analyze_fit(text, jd_input)
            
        # 2. Rewrite
        with st.spinner("Applying 'XYZ' Formula (GPT-4o)..."):
            resume_json = rewrite_resume(text, jd_input, analysis)
            docx_data = create_docx(resume_json)
            
        # Store Data
        st.session_state.analysis = analysis
        st.session_state.resume_json = resume_json
        st.session_state.docx_data = docx_data
        st.session_state.processed = True

# --- RESULTS ---
if st.session_state.processed:
    st.divider()
    
    # Scores
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Match Score", f"{st.session_state.analysis['match_percentage']}%")
    with c2:
        st.metric("Missing Keywords", len(st.session_state.analysis['missing_keywords']))
    with c3:
        st.success(f"Advice: {st.session_state.analysis['summary_critique']}")
        
    # Sneak Peek
    st.divider()
    st.subheader("👀 Optimization Preview")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Original Summary (Generic):**")
        st.warning("(Hidden for Privacy)")
    with col_b:
        st.markdown("**AI Optimized (XYZ Formula):**")
        st.success(st.session_state.resume_json.get('summary'))

    # Download
    st.divider()
    st.subheader("📥 Download Final Resume")
    st.download_button(
        label="Download Editable Word Doc (.docx)",
        data=st.session_state.docx_data,
        file_name="Optimized_Resume.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
