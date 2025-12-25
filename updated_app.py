import streamlit as st
import json
import requests
import io
import os
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Load Config
load_dotenv()
st.set_page_config(page_title="Resume Architect AI", page_icon="📝", layout="wide")

# 2. CSS for Professional Look
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2b6cb0; color: white; font-weight: bold; }
    .resume-preview { background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1); color: black; }
</style>
""", unsafe_allow_html=True)

# 3. API Setup
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("🚨 API Key Missing.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- HELPER FUNCTIONS ---

def fetch_jd_from_url(url):
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, timeout=10)
        return response.text
    except Exception as e:
        return None

def create_docx(data):
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
    run.font.color.rgb = RGBColor(0, 51, 102)

    contact = doc.add_paragraph()
    contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contact.add_run(data.get('contact_info', 'Location | Email | Phone'))

    # Sections
    if data.get('summary'):
        doc.add_heading('PROFESSIONAL SUMMARY', level=1)
        doc.add_paragraph(data['summary'])

    if data.get('skills'):
        doc.add_heading('TECHNICAL SKILLS', level=1)
        if isinstance(data['skills'], dict):
            for category, items in data['skills'].items():
                p = doc.add_paragraph()
                p.add_run(f"{category}: ").bold = True
                p.add_run(items)
        else:
            doc.add_paragraph(str(data['skills']))

    if data.get('experience'):
        doc.add_heading('PROFESSIONAL EXPERIENCE', level=1)
        for job in data['experience']:
            p = doc.add_paragraph()
            run_role = p.add_run(f"{job.get('role', 'Role')} | {job.get('company', 'Company')}")
            run_role.bold = True
            run_role.font.size = Pt(11)
            if job.get('dates'):
                p.add_run(f"  ({job['dates']})").italic = True
            for bullet in job.get('bullets', []):
                doc.add_paragraph(bullet, style='List Bullet')

    if data.get('education'):
        doc.add_heading('EDUCATION', level=1)
        for edu in data['education']:
            doc.add_paragraph(f"{edu.get('degree', '')} - {edu.get('school', '')}")

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

def analyze_fit(resume_text, jd_text):
    prompt = f"""
    Act as a strict ATS. Compare RESUME vs JD.
    SCORING: 100% = Perfect match. <60% = Missing hard skills.
    Ignore Soft Skills.
    Return JSON: {{ "match_percentage": Integer, "missing_keywords": ["List"] }}
    JD: {jd_text[:4000]}
    RESUME: {resume_text[:4000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0, seed=42,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def rewrite_resume_to_json(resume_text, jd_text, gap_data):
    """
    Polished Professional Rewrite (No fake XYZ metrics).
    """
    prompt = f"""
    You are a Senior Editor. Polish this resume to target the JD.
    
    INSTRUCTIONS:
    1. **Authenticity:** Do not invent numbers. If the user didn't provide metrics, focus on clear, strong action verbs.
    2. **Integration:** Naturally weave these missing keywords into the experience: {gap_data['missing_keywords']}
    3. **Clarity:** Remove fluff. Make sentences punchy and professional.
    4. **Structure:** Return strictly JSON.

    JSON Structure:
    {{
        "name": "Candidate Name",
        "contact_info": "City | Email | Phone",
        "summary": "Revised Summary",
        "skills": {{"Category": "List"}},
        "experience": [
            {{
                "role": "Title",
                "company": "Company",
                "dates": "Dates",
                "bullets": ["Bullet 1", "Bullet 2"]
            }}
        ],
        "education": [{{ "degree": "Degree", "school": "University" }}]
    }}

    JD: {jd_text[:4000]}
    RESUME: {resume_text[:4000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5, # Balanced creativity
        seed=42,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- MAIN UI ---

st.title("🚀 Resume Architect AI")
st.markdown("Upload your resume and a JD. We will **Polish** it and add the **Keywords** you need.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. The Job")
    tab_text, tab_link = st.tabs(["Paste Text", "Paste Link"])
    with tab_text:
        jd_text_input = st.text_area("Paste Job Description", height=200)
    with tab_link:
        jd_url = st.text_input("Paste URL")
        fetched_jd = None
        if jd_url:
            with st.spinner("Fetching..."):
                fetched_jd = fetch_jd_from_url(jd_url)
                if fetched_jd: st.success("✅ JD Loaded")
                else: st.error("Failed to load URL.")

with col2:
    st.subheader("2. Your Resume")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if st.button("🚀 Analyze & Polish"):
    final_jd = jd_text_input if jd_text_input else fetched_jd
    if not final_jd or not uploaded_file:
        st.warning("Please provide both inputs.")
    else:
        with st.spinner("Reading PDF..."):
            reader = PdfReader(uploaded_file)
            original_text = ""
            for page in reader.pages:
                original_text += page.extract_text() + "\n"

        with st.spinner("Analyzing Gaps..."):
            original_analysis = analyze_fit(original_text, final_jd)

        with st.spinner("Polishing Content (Integrating Keywords)..."):
            resume_json = rewrite_resume_to_json(original_text, final_jd, original_analysis)
            docx_data = create_docx(resume_json)

        # Calculate Improvement
        new_text_str = json.dumps(resume_json)
        new_analysis = analyze_fit(new_text_str, final_jd)

        # --- RESULTS ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Original Score", f"{original_analysis['match_percentage']}%")
        with c2: st.metric("Optimized Score", f"{new_analysis['match_percentage']}%")
        with c3: st.metric("Improvement", f"+{new_analysis['match_percentage'] - original_analysis['match_percentage']}%")

        st.warning(f"**Keywords Added:** {', '.join(original_analysis['missing_keywords'])}")
        
        # --- PREVIEW SECTION (NEW) ---
        st.divider()
        st.subheader("👀 Preview Optimized Resume")
        
        # We render the JSON as a nice HTML preview
        preview_html = f"""
        <div class="resume-preview">
            <h1 style="text-align:center; color:#003366;">{resume_json.get('name')}</h1>
            <p style="text-align:center;">{resume_json.get('contact_info')}</p>
            <hr>
            <h3>PROFESSIONAL SUMMARY</h3>
            <p>{resume_json.get('summary')}</p>
            <h3>EXPERIENCE</h3>
        """
        
        for job in resume_json.get('experience', []):
            preview_html += f"<h4>{job.get('role')} | {job.get('company')}</h4>"
            preview_html += f"<i>{job.get('dates')}</i><ul>"
            for bullet in job.get('bullets', []):
                preview_html += f"<li>{bullet}</li>"
            preview_html += "</ul>"
            
        preview_html += "</div>"
        
        st.markdown(preview_html, unsafe_allow_html=True)
        
        # --- DOWNLOAD ---
        st.divider()
        st.subheader("📥 Download Final Version")
        st.download_button(
            label="Download Editable Word Doc (.docx)",
            data=docx_data,
            file_name="Optimized_Resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
