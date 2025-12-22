import streamlit as st
import json
from openai import OpenAI
from pypdf import PdfReader

# 1. Page Configuration
st.set_page_config(page_title="Smart Resume Analyzer", page_icon="🎯", layout="wide")

# 2. API Key Setup
api_key = st.secrets.get("OPENAI_API_KEY")

with st.sidebar:
    st.header("⚙️ Configuration")
    if api_key:
        st.success("API Connected ✅")
    else:
        st.error("API Key missing! Check Streamlit Secrets.")
        st.stop()
    
    st.info("This tool compares a Resume against a Job Description to verify fit.")

# 3. Main Interface
st.title("🎯 AI Resume & Job Fit Analyzer")
st.markdown("Paste a **Job Description** and upload a **Resume** to see the match score and get improvement tips.")

# Layout: Split screen for inputs
col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ The Job")
    # Text Area for Job Description
    jd_text = st.text_area("Paste Job Description (JD) here:", height=200)

with col2:
    st.subheader("2️⃣ The Resume")
    # File Uploader
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")

# 4. Logic: Only run if both inputs are present
if st.button("Analyze Match"):
    if not jd_text:
        st.warning("⚠️ Please paste a Job Description first.")
    elif not uploaded_file:
        st.warning("⚠️ Please upload a Resume PDF.")
    else:
        # Extract Text from PDF
        with st.spinner("Reading Resume..."):
            try:
                reader = PdfReader(uploaded_file)
                resume_text = ""
                for page in reader.pages:
                    resume_text += page.extract_text() + "\n"
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
                st.stop()

        # AI Analysis
        with st.spinner("Comparing Resume to Job Description..."):
            client = OpenAI(api_key=api_key)
            
            # The Prompt: This is the 'brain' that compares the two texts
            prompt = f"""
            Act as an expert ATS (Applicant Tracking System) and Career Coach.
            
            I will provide a JOB DESCRIPTION and a RESUME. 
            Compare them and return a JSON object with the following fields:

            1. "match_percentage": Integer (0-100)
            2. "key_missing_skills": List of strings (Skills in JD but missing in Resume)
            3. "recommended_changes": List of strings (Specific advice to improve the resume for THIS job)
            4. "summary_of_fit": String (Brief explanation of why they fit or don't fit)

            JOB DESCRIPTION:
            {jd_text}

            RESUME TEXT:
            {resume_text}
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a JSON extractor and career coach."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                # Parse JSON
                data = json.loads(response.choices[0].message.content)

                # 5. Display Results
                st.divider()
                st.subheader("📊 Analysis Results")

                # Match Score Visual
                score = data.get('match_percentage', 0)
                
                # Create a progress bar with color logic
                st.metric("Match Score", f"{score}%")
                st.progress(score / 100)
                
                if score >= 80:
                    st.success("🎉 Great Match!")
                elif score >= 50:
                    st.warning("⚖️ Average Match - Needs Tweaking")
                else:
                    st.error("🛑 Low Match - Major Changes Needed")

                # Columns for details
                c1, c2 = st.columns(2)
                
                with c1:
                    st.write("### ❌ Missing Skills")
                    missing = data.get('key_missing_skills', [])
                    if missing:
                        for skill in missing:
                            st.write(f"- 🔴 {skill}")
                    else:
                        st.write("✅ No critical skills missing!")

                with c2:
                    st.write("### 💡 Recommendations")
                    recs = data.get('recommended_changes', [])
                    for rec in recs:
                        st.write(f"- 🔧 {rec}")

                # Summary
                st.write("### 📝 Verdict")
                st.info(data.get('summary_of_fit'))

            except Exception as e:
                st.error(f"An error occurred: {e}")