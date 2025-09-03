import os
import datetime
import smtplib
import json
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

# -----------------------------
# 1. Load credentials
# -----------------------------
load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")
GOOGLE_API_KEY = os.getenv("API_KEY")

# -----------------------------
# 2. Email sending function
# -----------------------------
def send_email(to_email: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        return f"✅ Email sent successfully to {to_email}"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"

# -----------------------------
# 3. Setup LLM with JSON parser
# -----------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    google_api_key=GOOGLE_API_KEY
)

response_schemas = [
    ResponseSchema(name="manager_name", description="The name of the manager"),
    ResponseSchema(name="manager_email", description="The email of the manager"),
    ResponseSchema(name="sender_name", description="The name of the sender"),
    ResponseSchema(name="sender_email", description="The email of the sender"),
    ResponseSchema(name="body", description="Polished email body without stars")
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
format_instructions = output_parser.get_format_instructions()

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an assistant that extracts email details and generates a polite daily status email."),
    ("human", """
From the following user input, extract:
- manager_name
- manager_email
- sender_name
- sender_email
- body

Output in JSON only.

User input:
{user_input}

{format_instructions}
""")
])

# -----------------------------
# 4. Streamlit UI
# -----------------------------
st.set_page_config(page_title="Daily Work Status Email Generator", page_icon="📧")

st.title("📧 Daily Work Status Email Generator")

user_input = st.text_area("Enter your full instructions in ONE prompt", height=200)

if st.button("Generate & Send Email"):
    if not user_input.strip():
        st.error("❌ Please enter your instructions first!")
    else:
        with st.spinner("🔍 Extracting details..."):
            _input = prompt.format_prompt(user_input=user_input, format_instructions=format_instructions)
            output = llm.invoke(_input.to_messages())

            try:
                parsed = output_parser.parse(output.content)
            except Exception as e:
                st.error("❌ Parsing error")
                st.code(output.content)
                st.stop()

            # Validate extracted details
            required_fields = ["manager_name", "manager_email", "sender_name", "sender_email", "body"]
            missing = [f for f in required_fields if not parsed.get(f)]

            if missing:
                st.error(f"❌ Missing fields: {missing}")
                st.json(parsed)
                st.stop()

            # Send email
            subject = f"Daily Work Status - {datetime.date.today()}"
            result = send_email(parsed["manager_email"], subject, parsed["body"])

            # Show results
            st.success("✅ Extraction Successful")
            st.json(parsed)

            st.subheader("📧 Email Status")
            st.write(result)
