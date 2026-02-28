import os
import base64
import io
import urllib.parse
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

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
    """
    Resize + compress uploaded image and convert to base64 data URL.
    Prevents huge iPhone images from breaking API calls.
    """
    image = Image.open(uploaded_file)

    # Resize if too large
    max_size = (1024, 1024)
    image.thumbnail(max_size)

    buffer = io.BytesIO()
    image = image.convert("RGB")  # ensure JPEG-safe
    image.save(buffer, format="JPEG", quality=80)
    buffer.seek(0)

    b64 = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def run_triage(pet_profile: dict, concerns: str, image_data_url: str | None) -> str:
    model = "gpt-4.1-mini"

    prompt_text = f"""
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
(brief summary: name, species, age, symptoms, timeline, appetite, water, vomiting/diarrhea, urination, energy, meds, toxins)

## Emergency red flags
(list key red flags and say to seek emergency care if present)

Pet profile:
- Name: {pet_profile.get("name")}
- Species: {pet_profile.get("species")}
- Breed: {pet_profile.get("breed")}
- Age: {pet_profile.get("age")}
- Weight: {pet_profile.get("weight")}
- Sex: {pet_profile.get("sex")}
- Known conditions: {pet_profile.get("conditions")}
- Current meds: {pet_profile.get("meds")}

Owner concerns:
{concerns}
""".strip()

    content = [{"type": "input_text", "text": prompt_text}]

    if image_data_url:
        content.append({"type": "input_image", "image_url": image_data_url})

    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": content}],
    )

    return response.output_text


# -----------------------------
# Background (paw pattern)
# -----------------------------
paw_svg = """
<svg xmlns="http://www.w3.org/2000/svg" width="260" height="260" viewBox="0 0 260 260">
  <g fill="rgba(255,255,255,0.06)">
    <!-- paw 1 -->
    <circle cx="60" cy="58" r="10"/>
    <circle cx="85" cy="50" r="8"/>
    <circle cx="105" cy="62" r="9"/>
    <circle cx="80" cy="78" r="14"/>
    <ellipse cx="85" cy="105" rx="26" ry="20"/>
    <!-- paw 2 -->
    <g transform="translate(130,120) rotate(-18)">
      <circle cx="20" cy="12" r="10"/>
      <circle cx="45" cy="5" r="8"/>
      <circle cx="65" cy="15" r="9"/>
      <circle cx="40" cy="32" r="14"/>
      <ellipse cx="45" cy="60" rx="26" ry="20"/>
    </g>
    <!-- paw 3 -->
    <g transform="translate(40,165) rotate(12)">
      <circle cx="20" cy="12" r="10"/>
      <circle cx="45" cy="5" r="8"/>
      <circle cx="65" cy="15" r="9"/>
      <circle cx="40" cy="32" r="14"/>
      <ellipse cx="45" cy="60" rx="26" ry="20"/>
    </g>
  </g>
</svg>
""".strip()

paw_bg = "data:image/svg+xml;utf8," + urllib.parse.quote(paw_svg)

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="Pet Health Helper", page_icon="🐾", layout="centered")

st.markdown(
    f"""
<style>
/* Background: dark + paw pattern */
.stApp {{
  background-color: #0f1117;
  background-image: url("{paw_bg}");
  background-repeat: repeat;
  background-size: 340px 340px;
}}

h1, h2, h3, p, li {{ color: #ffffff; }}
.small {{ color: #a0a6c0; font-size: 0.95rem; }}

/* Make content panels pop a little */
.block-container {{
  padding-top: 2.2rem;
  padding-bottom: 2rem;
}}
</style>
""",
    unsafe_allow_html=True,
)

st.title("🐾 Pet Health Helper")
st.markdown(
    '<div class="small">Upload a photo and describe symptoms. This tool provides triage guidance to help you decide how urgent vet care may be.</div>',
    unsafe_allow_html=True
)

with st.expander("Important safety note"):
    st.write(
        "This tool does NOT diagnose and is not a substitute for veterinary care. "
        "If your pet has trouble breathing, collapses, repeated vomiting, severe bleeding, seizures, "
        "bloated abdomen, cannot urinate, ingested toxins, or worsens rapidly — seek emergency care immediately."
    )

st.divider()

# Pet profile
st.markdown("### Pet Profile")
col0, col1, col2 = st.columns([1.2, 1, 1])

with col0:
    pet_name = st.text_input("Pet name", placeholder="e.g., Oso")
with col1:
    species = st.selectbox("Species", ["Dog", "Cat"])
with col2:
    sex = st.selectbox("Sex", ["Male", "Female", "Unknown"])

colA, colB = st.columns(2)
with colA:
    breed = st.text_input("Breed (optional)")
    age = st.text_input("Age")
with colB:
    weight = st.text_input("Weight (optional)")
    conditions = st.text_input("Known conditions (optional)")

meds = st.text_input("Current medications (optional)")

pet_profile = {
    "name": pet_name.strip() if pet_name else "Not provided",
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
    "Describe symptoms, timeline, appetite, water intake, vomiting/diarrhea, urination, energy level:",
    height=150
)

uploaded = st.file_uploader("Upload a photo (optional)", type=["jpg", "jpeg", "png", "webp"])

if uploaded:
    st.image(uploaded, caption="Uploaded photo", use_container_width=True)

st.divider()

# Vet finder
st.markdown("### Find a Vet")
location = st.text_input("City/State or ZIP")
if location:
    query = f"emergency vet near {location}"
    st.markdown(f"[Open in Google Maps](https://www.google.com/maps/search/{query.replace(' ', '+')})")

st.divider()

# Analyze
if st.button("Analyze & Generate Guidance", type="primary", use_container_width=True):

    if not concerns.strip():
        st.error("Please describe symptoms first.")
        st.stop()

    image_url = b64_data_url(uploaded) if uploaded else None

    with st.spinner("Analyzing..."):
        try:
            result_md = run_triage(pet_profile, concerns, image_url)
            title_name = pet_profile["name"] if pet_profile["name"] != "Not provided" else "your pet"
            st.markdown(f"## Results for {title_name}")
            st.markdown(result_md)
        except Exception as e:
            st.error("Something went wrong while analyzing. Try again or use a smaller image.")
            st.exception(e)