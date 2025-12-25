import streamlit as st
import json
from openai import OpenAI
from pypdf import PdfReader
from fpdf import FPDF
import base64

# 1. Page Config
st.set_page_config(page_title="AI Resume Optimizer", page_icon="🚀", layout="wide")

# 2. API Key
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("API Key missing!")
    st.stop()

client = OpenAI(api_key=api_key)

# --- HELPER FUNCTIONS ---

def get_analysis(resume_txt, jd_txt):
    """
    Analyzes the fit between resume and JD using STRICT criteria.
    """
    prompt = f"""
    Act as a ruthlessly efficient Applicant Tracking System (ATS) and Technical Recruiter.
    Compare the RESUME vs JOB DESCRIPTION.
    
    SCORING RULES:
    - 100%: Perfect match (Hard skills, years of exp, specific tools).
    - <60%: Missing critical keywords (e.g. knowing "Salesforce" but missing "APEX" for a dev role).
    
    CRITICAL INSTRUCTION:
    - Ignore "Soft Skills" like "Leadership" or "Communication" in the missing keywords list. 
    - Focus ONLY on Hard Skills, Tools, Certifications, and Frameworks.

    Return strictly JSON:
    {{
        "match_percentage": Integer (0-100),
        "missing_keywords": List[String] (Only hard skills),
        "summary": String (Brutal 2-sentence assessment of why they fit or fail)
    }}
    
    JOB DESCRIPTION: {jd_txt[:5000]}
    RESUME: {resume_txt[:5000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0, # Lock creativity for consistent scoring
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def generate_improved_content(resume_txt, jd_txt):
    """
    Rewrites the resume using the 'Google XYZ Formula' for maximum impact.
    """
    prompt = f"""
    You are a Top-Tier Executive Resume Writer. 
    Rewrite the provided RESUME to perfectly target the JOB DESCRIPTION.
    
    THE "GOLD STANDARD" FORMULA (Must Use):
    Do not just list duties. Use the Google XYZ formula:
    "Accomplished [X] as measured by [Y], by doing [Z]".
    (e.g., "Reduced server latency by 40% (Y) by refactoring API endpoints (Z), saving $10k/month (X).")
    
    INSTRUCTIONS:
    1. **Formatting:** Return PLAIN TEXT only. Use UPPERCASE for section headers (SUMMARY, SKILLS, EXPERIENCE).
    2. **Summary:** Write a punchy 3-line summary incorporating the JD's top 3 keywords.
    3. **Skills:** List Hard Skills first.
    4. **Experience:** Rewrite bullet points using the XYZ formula. Invent plausible metrics (estimates) if the original lacks them (e.g., "improved efficiency by ~20%").
    5. **Integration:** Naturally weave these missing keywords into the bullets: (Extract them from JD).
    
    Output Format (Plain Text):
    
    PROFESSIONAL SUMMARY
    [Text]
    
    TECHNICAL SKILLS
    [Text]
    
    PROFESSIONAL EXPERIENCE
    [Role] | [Company] | [Dates]
    - [XYZ Bullet 1]
    - [XYZ Bullet 2]
    
    EDUCATION
    [Text]
    
    JOB DESCRIPTION: {jd_txt[:5000]}
    RESUME: {resume_txt[:5000]}
    """
    response = client.chat.completions.create(
        model="gpt-4o", # Using the Smart Model
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7 # Slight creativity for writing flow
    )
    return response.choices[0].message.content

def create_pdf(text):
    """
    Converts plain text to a simple PDF file.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)
    
    # FPDF has trouble with some unicode characters, so we sanitize a bit
    # 'latin-1' encoding allows basic English text.
    safe_text = text.encode('latin-1', 'ignore').decode('latin-1')
    
    pdf.multi_cell(0, 10, safe_text)
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN UI ---

st.title("🚀 AI Resume Optimizer")
st.markdown("Upload your resume and a job description. We will **Analyze it**, **Rewrite it**, and **Rescore it**.")

col1, col2 = st.columns(2)
with col1:
    jd_input = st.text_area("Paste Job Description", height=200)
with col2:
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")

if st.button("Optimize Resume"):
    if not jd_input or not uploaded_file:
        st.warning("Please provide both a Job Description and a Resume.")
    else:
        # 1. Read Original PDF
        with st.spinner("Reading original resume..."):
            reader = PdfReader(uploaded_file)
            original_text = ""
            for page in reader.pages:
                original_text += page.extract_text() + "\n"

        # 2. Analyze Original Fit
        with st.spinner("Analyzing current fit..."):
            original_analysis = get_analysis(original_text, jd_input)

        # 3. Generate NEW Resume Content
        with st.spinner("Generating optimized resume version..."):
            improved_text = generate_improved_content(original_text, jd_input)

        # 4. Analyze NEW Fit
        with st.spinner("Checking score of new version..."):
            new_analysis = get_analysis(improved_text, jd_input)

        # 5. Create PDF
        pdf_data = create_pdf(improved_text)

        # --- DISPLAY RESULTS ---
        st.divider()
        st.subheader("📊 Optimization Results")

        # Score Comparison
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.metric("Original Score", f"{original_analysis['match_percentage']}%")
        
        with col_b:
            st.metric("Optimized Score", f"{new_analysis['match_percentage']}%")
        
        with col_c:
            improvement = new_analysis['match_percentage'] - original_analysis['match_percentage']
            st.metric("Improvement", f"+{improvement}%")
            
        # Visual Progress
        st.write("Match Improvement:")
        st.progress(new_analysis['match_percentage'] / 100)

        # Feedback
        st.write("### 🔍 What Changed?")
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"**Before:** {original_analysis['summary']}")
            st.write("**Missing Keywords (Fixed):**")
            if original_analysis['missing_keywords']:
                st.write(", ".join(original_analysis['missing_keywords']))
            else:
                st.write("None! Perfect Match.")
        with c2:
            st.success(f"**After:** {new_analysis['summary']}")
        
        # Download Button
        st.divider()
        st.subheader("📥 Download Your New Resume")
        st.markdown("This version is text-based and optimized for ATS reading.")
        
        st.download_button(
            label="Download Optimized Resume (PDF)",
            data=pdf_data,
            file_name="Optimized_Resume.pdf",
            mime="application/pdf"
        )
        
        # Show text preview
        with st.expander("Preview New Resume Text"):
            st.text(improved_text)
