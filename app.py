import os
import base64
import textwrap
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------
# Keys (Streamlit Cloud + local)
# -----------------------------
load_dotenv()

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    st.error("Missing OPENAI_API_KEY. Add it to Streamlit Secrets (TOML) or to a local .env file.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# Helpers
# -----------------------------
def b64_data_url(uploaded_file) -> str:
    """Convert an uploaded image file to a base64 data URL for the API."""
    data = uploaded_file.getvalue()
    b64 = base64.b64encode(data).decode("utf-8")
    mime = uploaded_file.type or "image/jpeg"
    return f"data:{mime};base64,{b64}"

def run_triage(pet_profile: dict, concerns: str, image_data_url: str | None) -> str:
    """
    Ask the model to provide triage-style guidance (not diagnosis).
    Returns formatted markdown.
    """
    # Choose a vision-capable model if you pass an image.
    # If you want: set model="gpt-4.1" (commonly used for vision) or another vision-capable model in your account.
    model = "gpt-4.1"

    # Build the input content
    content = [
        {
            "type": "text",
            "text": f"""
You are a pet health triage assistant. You are NOT a veterinarian and you must not diagnose.
Your job: help the user understand urgency, safe do/don't steps, and what to ask/tell a vet.

Rules:
- Do NOT provide medication dosing.
- Do NOT claim certainty or a diagnosis.
- Provide an urgency level: HOME / VET SOON (24-48h) / URGENT (same day) / EMERGENCY (now).
- If any red flags are present, choose EMERGENCY and explain why.
- Be concise and actionable.

Return your answer in Markdown with these exact sections:

## Urgency Level
(one of: HOME / VET SOON / URGENT / EMERGENCY)

## What this could be (possibilities to discuss with a vet)
(3-6 bullets; framed as possibilities, not diagnosis)

## Immediate safe steps
(5-8 bullets; safe, general care)

## Do NOT do
(5-8 bullets; common unsafe actions)

## Questions to answer (to improve accuracy)
(5-10 bullets the owner can check quickly)

## What to tell the vet (copy/paste)
(brief summary: species, age, symptoms, timeline, appetite, water, vomiting/diarrhea, urination, energy, meds, toxins)

## Emergency red flags
(list the key red flags and tell them to seek emergency care if present)

Pet profile:
- Species: {pet_profile.get("species")}
- Breed: {pet_profile.get("breed")}
- Age: {pet_profile.get("age")}
- Weight: {pet_profile.get("weight")}
- Sex: {pet_profile.get("sex")}
- Known conditions: {pet_profile.get("conditions")}
- Current meds: {pet_profile.get("meds")}

Owner concerns / behavior description:
{concerns}
""".strip()
        }
    ]

    if image_data_url:
        content.append({"type": "image_url", "image_url": image_data_url})

    response = client.responses.create(
        model = "gpt-4.1-mini",
        input=[{"role": "user", "content": content}],
    )

    return response.output_text

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="Pet Health Helper", page_icon="🐾", layout="centered")

st.markdown(
    """
<style>
.stApp { background-color: #0f1117; }
h1, h2, h3, p, li { color: #ffffff; }
.small { color: #a0a6c0; font-size: 0.95rem; }
.card {
  background: #1c1e2e;
  border: 1px solid #2e3148;
  border-radius: 14px;
  padding: 1rem 1.2rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("🐾 Pet Health Helper")
st.markdown(
    '<div class="small">Upload a photo and describe symptoms/behavior. This tool provides triage guidance and helps you decide how urgent it is to contact a vet.</div>',
    unsafe_allow_html=True
)

with st.expander("Important safety note (read)"):
    st.write(
        "This app is not a substitute for veterinary care. It does not diagnose. "
        "If your pet has trouble breathing, collapses, has repeated vomiting, severe bleeding, seizures, "
        "bloated abdomen, can't urinate, has eaten a toxin, or seems rapidly worse: seek emergency veterinary care."
    )

st.divider()

# Pet profile inputs
st.markdown("### Pet profile")
col1, col2 = st.columns(2)
with col1:
    species = st.selectbox("Species", ["Dog", "Cat", "Other"])
    breed = st.text_input("Breed (optional)", "")
    age = st.text_input("Age (e.g., 2 years, 10 months)", "")
with col2:
    weight = st.text_input("Weight (optional)", "")
    sex = st.selectbox("Sex", ["Unknown", "Male", "Female"])
    conditions = st.text_input("Known conditions (optional)", "")
meds = st.text_input("Current medications/supplements (optional)", "")

pet_profile = {
    "species": species,
    "breed": breed,
    "age": age,
    "weight": weight,
    "sex": sex,
    "conditions": conditions,
    "meds": meds,
}

st.markdown("### What’s going on?")
concerns = st.text_area(
    "Describe symptoms and behavior (include when it started, changes in eating/drinking, vomiting/diarrhea, urination, energy level).",
    height=160,
    placeholder="Example: Started yesterday. Less energy, not eating much, vomited once, drinking water, normal urination...",
)

uploaded = st.file_uploader("Upload a photo (optional but helpful)", type=["jpg", "jpeg", "png", "webp"])

if uploaded:
    st.image(uploaded, caption="Uploaded photo", use_container_width=True)

st.divider()

# Vet finder helper
st.markdown("### Find a vet")
location = st.text_input("City/State or ZIP (for a quick search link)", "")
if location:
    query = f"emergency vet near {location}" if species in ["Dog", "Cat"] else f"vet near {location}"
    st.markdown(f"- Search: **{query}**")
    st.markdown(f"- Open in Google Maps: https://www.google.com/maps/search/{query.replace(' ', '+')}")

st.divider()

# Run
if st.button("Analyze & generate guidance", type="primary", use_container_width=True):
    if not concerns.strip():
        st.error("Please describe symptoms/behavior first.")
        st.stop()

    image_url = b64_data_url(uploaded) if uploaded else None

    with st.spinner("Analyzing…"):
        result_md = run_triage(pet_profile, concerns, image_url)

    st.markdown("## Results")
    st.markdown(result_md)