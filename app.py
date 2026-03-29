import streamlit as st
import anthropic
import base64
import yaml
from pathlib import Path

st.set_page_config(
    page_title="Email Subject Generator",
    page_icon="✉️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #0e0e0e;
    color: #e8e8e0;
}

section[data-testid="stSidebar"] {
    background: #151515;
    border-right: 1px solid #2a2a2a;
}

h1, h2, h3 {
    font-family: 'DM Sans', sans-serif;
    font-weight: 300;
    letter-spacing: -0.02em;
    color: #e8e8e0;
}

.block-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 6px;
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 6px !important;
    color: #e8e8e0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #555 !important;
    box-shadow: none !important;
}

.stButton > button {
    background: #e8e8e0 !important;
    color: #0e0e0e !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    padding: 10px 24px !important;
    width: 100% !important;
    transition: opacity 0.15s !important;
}

.stButton > button:hover {
    opacity: 0.85 !important;
}

.stFileUploader > div {
    background: #1a1a1a !important;
    border: 1px dashed #333 !important;
    border-radius: 8px !important;
}

.yaml-output {
    background: #151515;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 20px 24px;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    line-height: 1.7;
    color: #c8c8c0;
    white-space: pre-wrap;
    overflow-x: auto;
}

.yaml-key   { color: #8ab4f8; }
.yaml-value { color: #c8c8c0; }

.hero-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
    color: #888;
}

.stat-pill {
    display: inline-block;
    background: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 20px;
    padding: 3px 12px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #666;
    margin-right: 6px;
}

div[data-testid="stSlider"] > div {
    color: #888 !important;
}

.stSlider > div > div > div > div {
    background: #e8e8e0 !important;
}

.stMarkdown p {
    color: #888;
    font-size: 14px;
}

hr {
    border-color: #222 !important;
}

.stSpinner > div {
    border-top-color: #e8e8e0 !important;
}

[data-testid="stImage"] img {
    border-radius: 6px;
    border: 1px solid #2a2a2a;
}
</style>
""", unsafe_allow_html=True)


SUPPORTED_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}

def get_mime(filename: str) -> str:
    ext = Path(filename).suffix.lstrip(".").lower()
    return SUPPORTED_MIME.get(ext, "image/jpeg")

def img_to_b64(file_bytes: bytes) -> str:
    return base64.standard_b64encode(file_bytes).decode("utf-8")

def generate_for_hero(
    client,
    email_b64, email_mime,
    hero_b64, hero_mime,
    existing_subject, existing_preview,
    num_variations,
) -> list[dict]:
    prompt = f"""You are an expert email marketing copywriter.

You are given two images:
1. An existing email design (first image) — use it to understand the brand tone, message, and style.
2. A new hero image variant (second image) — generate copy tailored to this visual.

Existing subject line: "{existing_subject}"
Existing preview text: "{existing_preview}"

Generate exactly {num_variations} variations of subject line + preview text for the new hero image.

Rules:
- Each variation must feel tailored to the visual mood and content of the NEW hero image
- Maintain the email's core message, tone, and style from the existing email
- Vary the angle, hook, or phrasing across variations — do not repeat patterns
- Keep subject lines concise (under 60 characters)
- Keep preview text under 90 characters

Return ONLY a valid YAML list with NO extra text, NO code fences, NO comments — just the raw list in this exact format:
- text: "..."
  preview_text: "..."
"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": email_mime, "data": email_b64}},
                {"type": "image", "source": {"type": "base64", "media_type": hero_mime, "data": hero_b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )

    raw = message.content[0].text.strip()
    raw = raw.removeprefix("```yaml").removeprefix("```yml").removeprefix("```").strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()

    parsed = yaml.safe_load(raw)
    if not isinstance(parsed, list):
        raise ValueError("Model returned unexpected format")
    return parsed


# ── Layout ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("## ✉️ Subject Generator")
    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown("<p class='block-label'>Anthropic API Key</p>", unsafe_allow_html=True)
    api_key = st.text_input("", type="password", placeholder="sk-ant-...", label_visibility="collapsed")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("<p class='block-label'>Variations per hero</p>", unsafe_allow_html=True)
    num_variations = st.slider("", min_value=1, max_value=10, value=5, label_visibility="collapsed")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("<p class='block-label'>Model</p>", unsafe_allow_html=True)
    model_choice = st.selectbox("", ["claude-opus-4-5", "claude-sonnet-4-5"], label_visibility="collapsed")


col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("### Existing email")

    st.markdown("<p class='block-label'>Email screenshot</p>", unsafe_allow_html=True)
    email_file = st.file_uploader("", type=["png","jpg","jpeg","webp"], key="email", label_visibility="collapsed")
    if email_file:
        st.image(email_file, use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<p class='block-label'>Subject line</p>", unsafe_allow_html=True)
    existing_subject = st.text_input("", placeholder="Your timer is running", key="subj", label_visibility="collapsed")

    st.markdown("<p class='block-label'>Preview text</p>", unsafe_allow_html=True)
    existing_preview = st.text_input("", placeholder="Final hours to get your reserved...", key="prev", label_visibility="collapsed")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("### New hero images")
    hero_files = st.file_uploader("", type=["png","jpg","jpeg","webp"], accept_multiple_files=True, key="heroes", label_visibility="collapsed")

    if hero_files:
        cols = st.columns(min(len(hero_files), 3))
        for i, hf in enumerate(hero_files):
            with cols[i % 3]:
                st.image(hf, caption=hf.name, use_container_width=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    generate_btn = st.button("GENERATE YAML →", use_container_width=True)


with col_right:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("### Output")

    if "yaml_result" not in st.session_state:
        st.session_state.yaml_result = None
    if "error_msg" not in st.session_state:
        st.session_state.error_msg = None

    if generate_btn:
        st.session_state.yaml_result = None
        st.session_state.error_msg = None

        if not api_key:
            st.session_state.error_msg = "Enter your Anthropic API key in the sidebar."
        elif not email_file:
            st.session_state.error_msg = "Upload an email screenshot."
        elif not existing_subject:
            st.session_state.error_msg = "Enter the existing subject line."
        elif not existing_preview:
            st.session_state.error_msg = "Enter the existing preview text."
        elif not hero_files:
            st.session_state.error_msg = "Upload at least one hero image."
        else:
            try:
                client = anthropic.Anthropic(api_key=api_key)
                email_b64 = img_to_b64(email_file.read())
                email_mime = get_mime(email_file.name)

                all_results = []
                progress = st.progress(0, text="Starting...")

                for i, hf in enumerate(hero_files):
                    progress.progress((i) / len(hero_files), text=f"Processing {hf.name}…")
                    hero_b64 = img_to_b64(hf.read())
                    hero_mime = get_mime(hf.name)

                    variations = generate_for_hero(
                        client,
                        email_b64, email_mime,
                        hero_b64, hero_mime,
                        existing_subject, existing_preview,
                        num_variations,
                    )

                    all_results.extend(variations)

                progress.progress(1.0, text="Done!")

                st.session_state.yaml_result = yaml.dump(
                    all_results,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )

            except Exception as e:
                st.session_state.error_msg = str(e)

    if st.session_state.error_msg:
        st.error(st.session_state.error_msg)

    if st.session_state.yaml_result:
        st.code(st.session_state.yaml_result, language="yaml")
        st.download_button(
            label="DOWNLOAD .yaml",
            data=st.session_state.yaml_result,
            file_name="subject_variations.yaml",
            mime="text/yaml",
            use_container_width=True,
        )
    else:
        st.markdown("""
<div style="
    border: 1px dashed #2a2a2a;
    border-radius: 8px;
    padding: 60px 24px;
    text-align: center;
    color: #444;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.08em;
">
    YAML output will appear here
</div>
""", unsafe_allow_html=True)
