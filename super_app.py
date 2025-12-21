import streamlit as st
import pandas as pd
import os
import json
import random
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# 1. Config & Setup
load_dotenv()
st.set_page_config(page_title="LBS AI Suite", page_icon="🚀", layout="wide")

# Sidebar Navigation
st.sidebar.title("🔮 AI Command Center")
app_mode = st.sidebar.radio("Select Module:", ["📄 Resume Architect (GenAI)", "📊 Donor Churn Predictor (ML)"])

# --- MODULE 1: RESUME ARCHITECT (GenAI) ---
if app_mode == "📄 Resume Architect (GenAI)":
    st.title("🤖 AI Resume Architect")
    st.markdown("### Screen candidates for Salesforce Architect roles using GPT-4.")

    # API Check
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OpenAI API Key missing! Check your .env file.")
        st.stop()

    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")

    if uploaded_file:
        # Extract Text
        with st.spinner("Extracting text from PDF..."):
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        
        st.success(f"PDF Loaded: {len(text)} characters extracted.")

        if st.button("Analyze Candidate"):
            with st.spinner("Consulting GPT-4..."):
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                prompt = f"""
                You are a Technical Recruiter for a Senior BA role.
                Extract these fields from the resume below and return JSON:
                1. "candidate_name" (String)
                2. "years_experience" (Integer estimate)
                3. "match_score" (Integer 0-100 based on fit for Salesforce Architect)
                4. "key_skills" (List of Strings)
                5. "missing_skills" (List of Strings - what do they lack?)
                6. "summary" (String - Professional verdict)

                RESUME:
                {text}
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                data = json.loads(response.choices[0].message.content)

                # Layout Results
                col1, col2, col3 = st.columns(3)
                col1.metric("Candidate Name", data['candidate_name'])
                col2.metric("Years Exp", f"{data['years_experience']}+")
                col3.metric("Match Score", f"{data['match_score']}/100")

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("✅ Key Skills")
                    for skill in data['key_skills']:
                        st.write(f"- {skill}")
                with c2:
                    st.subheader("⚠️ Missing / Gaps")
                    for gap in data['missing_skills']:
                        st.write(f"- {gap}")
                
                st.info(f"**Verdict:** {data['summary']}")

# --- MODULE 2: CHURN PREDICTOR (Predictive AI) ---
elif app_mode == "📊 Donor Churn Predictor (ML)":
    st.title("🔮 Donor Retention AI")
    st.markdown("### Predict if a donor will stop giving based on behavioral patterns.")

    # A. Load/Generate Data (Cached so it's fast)
    @st.cache_data
    def get_data():
        # Check if file exists, if not, generate it on the fly
        if not os.path.exists("donor_history.csv"):
            data = []
            regions = ['London', 'Manchester', 'Bristol', 'Global']
            for i in range(1001, 1501):
                region = random.choice(regions)
                freq = random.randint(1, 20)
                recency = random.randint(1, 365)
                amt = freq * random.randint(10, 100)
                # The Secret Rule
                prob = 0.1
                if recency > 180: prob += 0.6
                if region == 'London' and freq < 5: prob += 0.3
                churned = 1 if random.random() < prob else 0
                data.append([region, freq, recency, amt, churned])
            df = pd.DataFrame(data, columns=['Region', 'Frequency', 'Recency', 'TotalGiven', 'Churned'])
            return df
        return pd.read_csv("donor_history.csv")

    df = get_data()
    st.write(f"training model on {len(df)} historical records...")

    # B. Train Model (Cached Resource)
    @st.cache_resource
    def train_model(data):
        # Preprocessing
        df_encoded = pd.get_dummies(data, columns=['Region'], drop_first=True)
        X = df_encoded.drop(['Churned'], axis=1) # Drop ID if it exists, here we generated without ID for simplicity
        # Handle case where ID might be in CSV
        if 'ID' in X.columns: X = X.drop(['ID'], axis=1)
        
        y = df_encoded['Churned']
        
        # Train
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        return model, X.columns

    model, model_columns = train_model(df)
    st.success("✅ Model Trained & Ready!")

    st.divider()

    # C. The "What-If" Simulator
    st.subheader("simulator: Test a Donor Profile")
    
    col1, col2 = st.columns(2)
    with col1:
        input_recency = st.slider("Days Since Last Gift (Recency)", 0, 365, 150)
        input_freq = st.slider("Total Number of Gifts (Frequency)", 1, 50, 5)
    with col2:
        input_region = st.selectbox("Region", ["London", "Manchester", "Bristol", "Global"])
        input_amt = st.number_input("Total Amount Donated (£)", 10, 10000, 500)

    # D. Predict Button
    if st.button("Predict Churn Risk"):
        # Create a dataframe for the input
        input_data = pd.DataFrame({
            'Frequency': [input_freq],
            'Recency': [input_recency],
            'TotalGiven': [input_amt],
            'Region': [input_region]
        })
        
        # Encoding (must match training)
        input_encoded = pd.get_dummies(input_data, columns=['Region'], drop_first=True)
        # Add missing columns (e.g., if user selected London, Manchester column is missing)
        input_encoded = input_encoded.reindex(columns=model_columns, fill_value=0)
        
        prediction = model.predict(input_encoded)[0]
        prob = model.predict_proba(input_encoded)[0][1]

        if prediction == 1:
            st.error(f"🔴 HIGH RISK: {prob:.1%} probability of Churning")
            st.write("**Recommended Action:** Send 'We Miss You' automated email journey immediately.")
        else:
            st.success(f"🟢 SAFE: Only {prob:.1%} probability of Churning")
            st.write("**Recommended Action:** Add to 'Upgrade to Monthly' campaign.")