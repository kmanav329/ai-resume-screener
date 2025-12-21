import streamlit as st
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

# 1. Load Config
load_dotenv()
st.set_page_config(page_title="AI Resume Screener", page_icon="📄")

# 2. sidebar for API Key (Optional, but good practice)
with st.sidebar:
    st.header("Configuration")
    st.write("Ensuring API connection...")
    if os.getenv("OPENAI_API_KEY"):
        st.success("API Key Detected ✅")
    else:
        st.error("Missing .env file!")

# 3. Main Title
st.title("🤖 AI Resume Architect Screener")
st.write("Upload a PDF to see if the candidate fits the **Salesforce Architect** profile.")

# 4. File Uploader
uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")

if uploaded_file is not None:
    # 5. Extract Text (Handling the file in memory)
    with st.spinner("Reading PDF..."):
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    
    st.info(f"Extracted {len(text)} characters from resume.")

    # 6. Analyze with AI
    if st.button("Analyze Candidate"):
        with st.spinner("Consulting GPT-4..."):
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            prompt = f"""
            Extract the following fields from the resume text below and return strictly as JSON.
            
            Fields:
            1. "candidate_name" (String)
            2. "years_of_experience" (Integer)
            3. "salesforce_clouds" (List of Strings)
            4. "architect_skills" (List of Strings - e.g. ETL, API, Integration)
            5. "summary" (One sentence summary of fit)

            RESUME TEXT:
            {text}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a JSON extractor."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse JSON
            data = json.loads(response.choices[0].message.content)

            # 7. Display Results nicely
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(data['candidate_name'])
                st.write(f"**Experience:** {data['years_of_experience']} Years")
            
            with col2:
                # Logic: Check for Marketing Cloud
                clouds = [c.lower() for c in data['salesforce_clouds']]
                if any("marketing" in c for c in clouds):
                    st.success("✅ SFMC Expert")
                else:
                    st.warning("⚠️ No Marketing Cloud Detected")

            st.write("### ☁️ Cloud Experience")
            st.write(", ".join(data['salesforce_clouds']))

            st.write("### 🛠 Technical Skills")
            st.write(", ".join(data['architect_skills']))

            st.write("### 📝 AI Summary")
            st.info(data['summary'])

            # Raw JSON for the developer (you)
            with st.expander("View Raw JSON Data"):
                st.json(data)