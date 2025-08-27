# ui_helpers.py
import os, requests, streamlit as st

def init_flags():
    st.session_state.setdefault("ui_lang", "ar")
    st.session_state.setdefault("country_code", None)
    st.session_state.setdefault("is_owner", False)
    st.session_state.setdefault("show_paid_features", True)
    st.session_state.setdefault("free_search_used", False)
    st.session_state.setdefault("user_email", "")
    st.session_state.setdefault("articles_open", False)
    st.session_state.setdefault("services_open", False)
    st.session_state.setdefault("helpme_open", False)
    st.session_state.setdefault("helpme_work", None)

def detect_country(timeout=2.5):
    if st.session_state["country_code"]:
        return st.session_state["country_code"]
    try:
        r = requests.get("https://ipapi.co/json/", timeout=timeout)
        if r.ok: st.session_state["country_code"] = r.json().get("country_code")
    except Exception:
        st.session_state["country_code"] = None
    return st.session_state["country_code"]

def apply_paid_visibility():
    hide_in_eg = os.getenv("HIDE_PAID_FEATURES_IN_EG","true").lower()=="true"
    cc = st.session_state.get("country_code")
    is_owner = st.session_state.get("is_owner", False)
    st.session_state["show_paid_features"] = True
    if hide_in_eg and (cc=="EG") and not is_owner:
        st.session_state["show_paid_features"] = False

def owner_badge():
    if st.session_state.get("is_owner"):
        st.markdown("<div style='padding:4px 8px;background:#DCFCE7;border:1px solid #16A34A;border-radius:8px;display:inline-block'>Owner mode</div>", unsafe_allow_html=True)

def watermark_css(name):
    st.markdown(f"""
    <style>
    body::before {{
        content: "{name}";
        position: fixed; top:40%; left:10%;
        font-size: 48px; color: rgba(0,0,0,0.06);
        transform: rotate(-20deg); z-index:0; pointer-events:none;
    }}
    .block-container {{ position: relative; z-index: 1; }}
    </style>
    """, unsafe_allow_html=True)

def footer_identity():
    owner_ar = os.getenv("OWNER_FULLNAME_AR","")
    owner_en = os.getenv("OWNER_FULLNAME_EN","")
    photo = os.getenv("OWNER_PHOTO_URL","")
    lang = st.session_state.get("ui_lang","ar")
    name = owner_ar if lang=="ar" else (owner_en or owner_ar)
    st.write("---")
    cols = st.columns([1,6,3])
    with cols[0]:
        if photo: st.image(photo, width=72)
    with cols[1]:
        st.markdown(f"**{name}**  \n© All rights reserved — Non-commercial use only.")
        st.markdown("[TERMS](https://docs.openalex.org/how-to-use-the-api/rate-limits-and-mailto) · [EULA](/EULA.md) · [SECURITY](/SECURITY.md)")
    with cols[2]:
        owner_badge()
