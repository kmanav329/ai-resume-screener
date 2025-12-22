import streamlit as st
import json
from openai import OpenAI
from pypdf import PdfReader
from xhtml2pdf import pisa
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Salesforce Career Architect", page_icon="☁️", layout="wide")

# API Setup
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("🚨 API Key Missing. Please check Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- CSS / HTML TEMPLATES ---
# This is the design of the resume. You can change colors here.
RESUME_CSS = """
<style>
    @page { size: a4 portrait; margin: 2cm; }
    body { font-family: Helvetica, sans-serif; color: #333; line-height: 1.5; }
    h1 { color: #0070d2; font-size: 24pt; margin-bottom: 5px; text-transform: uppercase; } /* Salesforce Blue */
    h2 { color: #333; font-size: 14pt; border-bottom: 2px solid #0070d2; padding-bottom: 5px; margin-top: 20px; }
    .contact-info { font-size: 10pt; color: #666; margin-bottom: 20px; }
    .job-title { font-weight: bold; font-size: 11pt; margin-top: 10px; }
    .company { font-style: italic; color: #555; }
    ul { margin-top: 5px; }
    li { font-size: 10pt; margin-bottom: 5px; }
    .skills-box { background-color: #f4f6f9; padding: 10px; border-radius: 5px; font-size: 10pt; margin-bottom: 15px; }
</style>
"""

# --- HELPER FUNCTIONS ---

def pdf_from_html(html_content):
    """
    Converts HTML string to PDF bytes using xhtml2pdf.
    """
    pdf_file = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
    if pisa_status.err:
        return None
    return pdf_file.getvalue()

def analyze_gap(resume_text, jd_text):
    """
    Uses GPT-4o-mini (Cheap) to analyze the gap.
    """
    prompt = f"""
    You are a Senior Salesforce Recruiter & Technical Architect.
    Analyze the RESUME against the JOB DESCRIPTION (JD).
    
    Identify:
    1. Match Score (0-100).
    2. Missing Hard Skills (Specific Salesforce Clouds, Tools, Languages like APEX, LWC, AMPScript).
    3. Critical Missing Certifications.
    
    Return strictly JSON:
    {{
        "score": 0,
        "missing_skills": ["skill1", "skill2"],
        "missing_certs": ["cert1"],
        "advice": "Strategic advice..."
    }}

    RESUME: {resume_text[:3000]}
    JD: {jd_text[:3000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def generate_optimized_content(resume_text, jd_text, gap_analysis):
    """
    Uses GPT-4o (Smart) to REWRITE the resume in HTML format.
    """
    prompt = f"""
    You are a Professional Resume Writer specializing in the Salesforce Ecosystem.
    Rewrite the candidate's resume to perfectly target the Job Description.

    INPUT DATA:
    - Missing Skills to Integrate: {gap_analysis['missing_skills']}
    - Job Context: {jd_text[:2000]}
    - Original Resume: {resume_text[:3000]}

    INSTRUCTIONS:
    1. Output ONLY valid HTML code inside a <body> tag. DO NOT include <html> or <head> tags.
    2. Use the following structure:
       - <h1>Name</h1>
       - <div class="contact-info">Phone | Email | LinkedIn | Location</div>
       - <div class="skills-box"><strong>Technical Skills:</strong> [Insert Optimized Skills Here]</div>
       - <h2>Professional Experience</h2>
       - [For each job]: <div class="job-title">Role</div> <div class="company">Company | Dates</div>
         <ul>
           <li>[STAR Method Bullet Point 1 - Quantified results]</li>
           <li>[STAR Method Bullet Point 2 - integrated missing keywords]</li>
         </ul>
       - <h2>Education & Certifications</h2>
    
    3. CRITICAL: Naturally weave the 'Missing Skills' into the bullet points. e.g., instead of "Sent emails", say "Orchestrated Journey Builder campaigns using AMPScript..."
    4. Keep it professional and clean.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o", # Using the SMART model for writing
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def generate_cover_letter(resume_text, jd_text):
    """
    Generates a cover letter.
    """
    prompt = f"""
    Write a compelling, professional Cover Letter for this Salesforce role.
    
    Rules:
    1. Tone: Enthusiastic, Professional, Confident.
    2. Connect the candidate's specific experience to the JD's requirements.
    3. Keep it under 300 words.
    4. Return plain text (not HTML).
    
    RESUME: {resume_text[:2000]}
    JD: {jd_text[:2000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- MAIN UI ---

st.title("☁️ Salesforce/Tech Resume Architect")
st.markdown("Optimize your profile for **Salesforce, Marketing Cloud, and Developer** roles using AI.")

# Session State to hold data across clicks
if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'optimized_html' not in st.session_state:
    st.session_state.optimized_html = None
if 'cover_letter' not in st.session_state:
    st.session_state.cover_letter = None

# Input Section
with st.expander("📂 Upload & Configuration", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        jd_input = st.text_area("Paste Job Description (JD)", height=200, placeholder="Paste the LinkedIn/Indeed JD here...")
    with col2:
        uploaded_file = st.file_uploader("Upload Current Resume (PDF)", type="pdf")

# Process Button
if st.button("🚀 Analyze & Optimize Profile"):
    if not jd_input or not uploaded_file:
        st.warning("⚠️ Please provide both a JD and a PDF.")
    else:
        # 1. Read PDF
        with st.spinner("Parsing Resume..."):
            reader = PdfReader(uploaded_file)
            resume_text = ""
            for page in reader.pages:
                resume_text += page.extract_text() + "\n"
        
        # 2. Analyze (Gap Analysis)
        with st.spinner("Conducting Gap Analysis (GPT-4o-mini)..."):
            st.session_state.analysis = analyze_gap(resume_text, jd_input)
            
        # 3. Write Resume (HTML)
        with st.spinner("Drafting Optimized Resume (GPT-4o)..."):
            raw_html = generate_optimized_content(resume_text, jd_input, st.session_state.analysis)
            # Combine CSS with the generated Body
            st.session_state.optimized_html = f"<html><head>{RESUME_CSS}</head><body>{raw_html}</body></html>"

        # 4. Write Cover Letter
        with st.spinner("Drafting Cover Letter..."):
            st.session_state.cover_letter = generate_cover_letter(resume_text, jd_input)
            
        st.success("Processing Complete! Check the tabs below.")

# --- RESULTS DISPLAY ---

if st.session_state.analysis:
    
    tab1, tab2, tab3 = st.tabs(["📊 Analysis Report", "📄 Optimized Resume", "✉️ Cover Letter"])
    
    # TAB 1: Analysis
    with tab1:
        data = st.session_state.analysis
        
        # Score
        col_a, col_b = st.columns([1, 3])
        with col_a:
            st.metric("Match Score", f"{data['score']}%")
        with col_b:
            st.progress(data['score'] / 100)
            
        # Details
        c1, c2 = st.columns(2)
        with c1:
            st.error("🚨 Missing Skills / Keywords")
            for skill in data['missing_skills']:
                st.write(f"- {skill}")
        with c2:
            st.warning("🎓 Missing Certifications (Detected)")
            if data.get('missing_certs'):
                for cert in data['missing_certs']:
                    st.write(f"- {cert}")
            else:
                st.write("No major certification gaps detected.")
                
        st.info(f"💡 **Strategic Advice:** {data['advice']}")

    # TAB 2: Optimized Resume
    with tab2:
        st.subheader("Your New Salesforce-Ready Resume")
        st.markdown("This version uses the **STAR method** and integrates missing keywords.")
        
        # Download Button
        pdf_bytes = pdf_from_html(st.session_state.optimized_html)
        if pdf_bytes:
            st.download_button(
                label="📥 Download PDF Resume",
                data=pdf_bytes,
                file_name="Optimized_Salesforce_Resume.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Error generating PDF.")

        # HTML Preview (Safe Sandbox)
        st.components.v1.html(st.session_state.optimized_html, height=800, scrolling=True)

    # TAB 3: Cover Letter
    with tab3:
        st.subheader("Tailored Cover Letter")
        cl_text = st.session_state.cover_letter
        st.text_area("Copy your cover letter:", value=cl_text, height=400)
        
        st.download_button(
            label="📥 Download Cover Letter (.txt)",
            data=cl_text,
            file_name="Cover_Letter.txt"
        )
