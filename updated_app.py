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
    Analyzes the fit between resume and JD.
    Returns a JSON object with score and feedback.
    """
    prompt = f"""
    Act as an expert ATS. Compare the RESUME vs JOB DESCRIPTION.
    Return strictly JSON:
    {{
        "match_percentage": Integer (0-100),
        "missing_keywords": List[String],
        "summary": String
    }}
    
    JOB DESCRIPTION: {jd_txt}
    RESUME: {resume_txt}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def generate_improved_content(resume_txt, jd_txt):
    """
    Rewrites the resume to include keywords and fit the JD.
    """
    prompt = f"""
    You are a professional Resume Writer. 
    Rewrite the provided RESUME to target the JOB DESCRIPTION.
    
    Rules:
    1. Keep the candidate's real truth (don't lie), but emphasize relevant skills.
    2. Naturally include missing keywords from the JD.
    3. Use professional, clear language.
    4. Structure it clearly (Summary, Skills, Experience, Education).
    5. Return ONLY the body text of the new resume. Do not include Markdown or JSON. Just plain text.
    
    JOB DESCRIPTION: {jd_txt}
    RESUME: {resume_txt}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
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
            st.write(", ".join(original_analysis['missing_keywords']))
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
