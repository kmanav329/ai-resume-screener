import streamlit as st
import json
from openai import OpenAI
from pypdf import PdfReader
from fpdf import FPDF, HTMLMixin

# --- CONFIGURATION ---
st.set_page_config(page_title="Salesforce Resume Architect", page_icon="☁️", layout="wide")

api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("🚨 API Key Missing. Please check Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- PDF GENERATOR CLASS ---
class PDF(FPDF, HTMLMixin):
    def header(self):
        self.set_font("Helvetica", 'B', 10)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "Salesforce Career Architect | AI Optimized", align="R")
        self.ln(15)

# --- AI LOGIC ---

def analyze_gap(resume_text, jd_text):
    """
    Cheap model (GPT-4o-mini) to find the flaws.
    """
    prompt = f"""
    You are a Technical Recruiter for Salesforce.
    Compare the RESUME vs JOB DESCRIPTION.
    
    Return JSON:
    {{
        "match_score": Integer (0-100),
        "missing_hard_skills": ["List", "of", "exact", "keywords"],
        "advice": "One sentence strategic advice."
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

def generate_optimized_resume(resume_text, jd_text, gap_data):
    """
    Smart model (GPT-4o) to rewrite the resume.
    """
    prompt = f"""
    You are a Professional Resume Writer. Rewrite this resume for the specific Job Description.
    
    MANDATORY INSTRUCTIONS:
    1. Integrate these missing skills naturally into bullet points: {gap_data['missing_hard_skills']}
    2. Use the STAR method (Situation, Task, Action, Result).
    3. Return ONLY valid HTML supported by FPDF2.
    
    FORMATTING RULES (Strict):
    - Use <h1> for Name (Center aligned).
    - Use <p> for contact info (Center aligned).
    - Use <h3> for Section Headers (Summary, Skills, Experience, Education).
    - Use <b> for Bold keywords.
    - Use <ul> and <li> for experience bullets.
    - NO <style> or CSS classes.
    
    STRUCTURE:
    <h1 align="center">Candidate Name</h1>
    <p align="center">Location | Email | Phone</p>
    
    <h3>PROFESSIONAL SUMMARY</h3>
    <p>...strong summary...</p>
    
    <h3>TECHNICAL SKILLS</h3>
    <p><b>Salesforce:</b> ...</p>
    
    <h3>EXPERIENCE</h3>
    <b>Role</b> - Company<br>
    <i>Dates</i>
    <ul>
       <li>...bullet...</li>
    </ul>

    RESUME: {resume_text[:3000]}
    JD: {jd_text[:3000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def generate_cover_letter(resume_text, jd_text):
    """
    Writes a persuasive cover letter.
    """
    prompt = f"""
    Write a short, punchy Cover Letter for this Salesforce role.
    Focus on why the candidate is a technical fit.
    Do not use placeholders like [Your Name] - use the data from the resume if possible, or generic placeholders.
    
    RESUME: {resume_text[:3000]}
    JD: {jd_text[:3000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- UI LAYOUT ---

st.title("☁️ Salesforce Resume Architect")
st.markdown("Upload your generic resume and a specific JD. We will **Rewrite** it and generate a **Cover Letter**.")

# 1. Inputs
col1, col2 = st.columns(2)
with col1:
    jd_input = st.text_area("Paste Job Description", height=200, placeholder="Paste JD here...")
with col2:
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")

# 2. State Management (Prevents data loss on reload)
if 'processed' not in st.session_state:
    st.session_state.processed = False
    st.session_state.analysis = None
    st.session_state.pdf_data = None
    st.session_state.cover_letter = None

# 3. Action Button
if st.button("🚀 Analyze & Optimize"):
    if not jd_input or not uploaded_file:
        st.warning("Please provide both inputs!")
    else:
        # Extract Text
        reader = PdfReader(uploaded_file)
        text = "".join([page.extract_text() for page in reader.pages])
        
        # Step A: Analyze
        with st.spinner("Analyzing Gaps..."):
            st.session_state.analysis = analyze_gap(text, jd_input)
        
        # Step B: Rewrite Resume
        with st.spinner("Rewriting Resume (GPT-4o)..."):
            html_content = generate_optimized_resume(text, jd_input, st.session_state.analysis)
            
            # Create PDF
            pdf = PDF()
            pdf.add_page()
            try:
                pdf.write_html(html_content)
                st.session_state.pdf_data = pdf.output(dest='S')
            except Exception as e:
                st.error(f"PDF formatting error: {e}")
                
        # Step C: Write Cover Letter
        with st.spinner("Drafting Cover Letter..."):
            st.session_state.cover_letter = generate_cover_letter(text, jd_input)
            
        st.session_state.processed = True

# 4. Display Results
if st.session_state.processed:
    st.divider()
    
    # Metrics
    c1, c2 = st.columns([1, 3])
    with c1:
        score = st.session_state.analysis['match_score']
        st.metric("Match Score", f"{score}%")
    with c2:
        st.info(f"**Advice:** {st.session_state.analysis['advice']}")
        if st.session_state.analysis['missing_hard_skills']:
            st.write(f"**Integrated Missing Keywords:** {', '.join(st.session_state.analysis['missing_hard_skills'])}")

    # Tabs for Outputs
    tab1, tab2 = st.tabs(["📄 Optimized Resume", "✉️ Cover Letter"])
    
    with tab1:
        st.success("Resume rewritten with STAR method and keywords integrated.")
        st.download_button(
            label="📥 Download Resume PDF",
            data=st.session_state.pdf_data,
            file_name="Optimized_Salesforce_Resume.pdf",
            mime="application/pdf"
        )
        
    with tab2:
        st.subheader("Draft Cover Letter")
        st.text_area("Edit Content:", value=st.session_state.cover_letter, height=300)
        st.download_button(
            label="📥 Download Cover Letter (.txt)",
            data=st.session_state.cover_letter,
            file_name="Cover_Letter.txt"
        )
