# search_it_pro_i18n_full.py  (Streamlit UI)
import os, re, io, requests, pandas as pd, streamlit as st
from ui_helpers import init_flags, detect_country, apply_paid_visibility, footer_identity, owner_badge, watermark_css

BACKEND_URL = os.getenv("BACKEND_URL") or st.secrets.get("BACKEND_URL","http://localhost:8001")

st.set_page_config(page_title="Search It — Pro", layout="wide")

def valid_email(x:str)->bool:
    return bool(x and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"))

# ===== Helpers (UI) =====
def to_dataframe(results):
    rows=[]
    for w in results:
        title = w.get("title") or w.get("display_name") or ""
        doi = w.get("doi","")
        year = (w.get("publication_year") or "")
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name","")
        rows.append({"Title": title, "Year": year, "Venue": venue, "DOI": doi})
    return pd.DataFrame(rows)

def get_best_pdf_and_source(w):
    doi = (w.get("doi") or "").replace("https://doi.org/","")
    pdf = (w.get("open_access") or {}).get("oa_url") or ""
    source = ((w.get("primary_location") or {}).get("source") or {}).get("url") or ""
    if not source and doi:
        source = f"https://doi.org/{doi}"
    if (not pdf) and doi:
        try:
            r = requests.get(f"{BACKEND_URL}/resolve", params={"doi": doi}, timeout=8)
            if r.ok:
                j = r.json()
                pdf = j.get("oa_pdf_url") or pdf
                if not source: source = j.get("publisher_landing_url") or source
        except Exception:
            pass
    return pdf, source

def actions_row(w):
    pdf, source = get_best_pdf_and_source(w)
    parts=[]
    if pdf: parts.append(f'<a title="PDF" href="{pdf}" target="_blank">⬇ PDF</a>')
    if source: parts.append(f'<a title="From Source" href="{source}" target="_blank">↗ From Source</a>')
    parts.append('<a title="Cite" href="#cite">📝 Cite</a>')
    parts.append('<a title="Export" href="#export">📤 Export (RIS/BibTeX/CSL-JSON)</a>')
    parts.append('<a title="Translate" href="https://www.reverso.net/text-translation" target="_blank">🌐 Translate</a>')
    if pdf: parts.append('<a title="Chat with PDF" href="https://www.chatpdf.com/" target="_blank">💬 Chat with PDF</a>')
    if st.session_state.get("show_paid_features", True):
        if st.button("🆘 Help me", key=f"help_{w.get('id','')[:12]}"):
            st.session_state["helpme_open"]=True
            st.session_state["helpme_work"]=w
    return " | ".join(parts)

def render_results(results):
    st.write(f"**Results shown:** {len(results)}")
    for w in results:
        title = (w.get("title") or "Untitled").strip()
        authors = ", ".join([ (a.get("author") or {}).get("display_name","") for a in (w.get("authorships") or []) ][:5])
        year = w.get("publication_year") or ""
        st.markdown(f"### {title}")
        st.caption(f"{authors} · {year}")
        st.markdown(actions_row(w), unsafe_allow_html=True)
        st.divider()
    helpme_modal()
    services_modal()

def helpme_modal():
    if not st.session_state.get("helpme_open"): return
    w = st.session_state.get("helpme_work") or {}
    with st.modal("Help me — 20 questions ($20, bank transfer only)"):
        st.write((w.get("title") or "Selected paper").strip())
        QUESTIONS_EN = [
            "What problem/gap does the paper address?","What is the main research question/hypothesis?",
            "What methodology was used?","Is the sample size adequate?","What are the key variables and measures?",
            "Which statistical tests were used and why?","Were assumptions checked?",
            "Statistical significance and practical significance?","Are analyses aligned with questions/hypotheses?",
            "Key findings?","Limitations and potential biases?","Validity/Reliability of instruments?",
            "Alternative methods/analyses?","Novelty vs. literature?","Replicability/reproducibility?",
            "Ethics?","Quality of figures/tables?","Recency/balance of citations?","Future work suggestions?",
            "Executive summary (5–7 lines)."
        ]
        selected=[q for i,q in enumerate(QUESTIONS_EN,1) if st.checkbox(q, key=f"q{i}")]
        email = st.text_input("Email for OTP / البريد")
        if st.button("Send OTP"): requests.post(f"{BACKEND_URL}/bank/reveal", data={"email": email}, timeout=10); st.info("OTP sent.")
        otp = st.text_input("Enter OTP", key="help_otp")
        if st.button("Reveal bank"):
            r = requests.post(f"{BACKEND_URL}/bank/reveal", data={"email": email, "otp": otp}, timeout=10)
            if r.ok:
                bank = r.json(); st.json(bank)
                proof = st.file_uploader("Upload transfer proof (PDF/JPG/PNG)", type=["pdf","jpg","jpeg","png"])
                if proof and st.button("Submit proof"):
                    rr = requests.post(f"{BACKEND_URL}/bank/proof", files={"file": (proof.name, proof.getvalue())}, timeout=20)
                    if rr.ok: st.success("Proof received. Answers will be prepared.")
        if st.button("Close"): st.session_state["helpme_open"]=False

def services_modal():
    if not st.session_state.get("services_open"): return
    with st.modal("Services Center — bank transfer only"):
        svc = st.selectbox("Choose a service", [
            ("review_thesis", "Thesis Review — $50 deposit"),
            ("peer_review", "Peer Review — $50 deposit"),
            ("language_editing", "Language Editing (AR/EN/FR) — $50 deposit"),
            ("formatting", "Formatting (Paper/Thesis/Book) — $50 deposit"),
            ("reference_check", "Reference Match & Citation Check — $50 deposit"),
            ("summarize_prior_studies", "Summarize prior studies (20–30) — $120"),
            ("instrument_consult", "Study Instruments Consultation — $50 deposit"),
        ], format_func=lambda x: x[1])
        name = st.text_input("Full name")
        email = st.text_input("Email")
        whatsapp = st.text_input("WhatsApp (+20…)")
        due = st.date_input("Approx. due date")
        notes = st.text_area("Notes (optional)")
        entries = ""
        files = st.file_uploader("Upload files (Word/PDF/Excel/CSV)", accept_multiple_files=True,
                                 type=["doc","docx","pdf","xls","xlsx","csv"])

        if svc[0]=="summarize_prior_studies":
            st.markdown("Paste 20–30 studies (one per line: Title — Authors — Link/DOI):")
            entries = st.text_area("Studies list")

        if st.button("Create request"):
            data = {"svc_type": svc[0], "name": name, "email": email, "whatsapp": whatsapp,
                    "due": str(due), "notes": notes, "entries": entries, "files_count": len(files or [])}
            r = requests.post(f"{BACKEND_URL}/svc/init", data=data, timeout=12)
            if r.ok: st.success(f"Request created. Deposit: ${r.json().get('deposit_usd')} — proceed with bank reveal below.")

        st.write("— Bank transfer (OTP → masked IBAN/SWIFT):")
        email_b = st.text_input("Confirm email for OTP", key="svc_email")
        if st.button("Send OTP", key="svc_otp_send"):
            requests.post(f"{BACKEND_URL}/bank/reveal", data={"email": email_b}, timeout=10); st.info("OTP sent.")
        otp_b = st.text_input("Enter OTP", key="svc_otp")
        if st.button("Reveal bank", key="svc_reveal"):
            r = requests.post(f"{BACKEND_URL}/bank/reveal", data={"email": email_b, "otp": otp_b}, timeout=10)
            if r.ok:
                bank = r.json(); st.json(bank)
                proof = st.file_uploader("Upload transfer proof", type=["pdf","jpg","jpeg","png"], key="svc_proof")
                if proof and st.button("Submit proof", key="svc_submit"):
                    rr = requests.post(f"{BACKEND_URL}/bank/proof", files={"file": (proof.name, proof.getvalue())}, timeout=20)
                    if rr.ok: st.success("Proof received. We will contact you via WhatsApp.")
        if st.button("Close", key="svc_close"): st.session_state["services_open"]=False

# ---------- Init & Geo ----------
init_flags()
detect_country()
apply_paid_visibility()

# ---------- Watermark (optional) ----------
if os.getenv("WATERMARK","true").lower()=="true":
    watermark_css(os.getenv("OWNER_FULLNAME_AR",""))

# ---------- Top bar ----------
c1,c2,c3,c4,c5 = st.columns([2,2,2,3,3])
with c1:
    st.markdown("### Search It — Pro")
with c2:
    if st.button("📰 Publish Articles"):
        st.session_state.articles_open = True
with c3:
    if st.session_state.get("show_paid_features", True):
        if st.button("🧰 Services"):
            st.session_state.services_open = True
with c4:
    st.write("")
with c5:
    owner_badge()

# ---------- Publish Articles modal ----------
if st.session_state.get("articles_open"):
    with st.modal("Publish Articles"):
        st.write("Use the Word template to draft your posts, then publish.")
        try:
            with open("Articles_Word_Template.docx","rb") as f:
                st.download_button("Download Word Template", f.read(), file_name="Articles_Word_Template.docx")
        except Exception:
            st.info("Template file not found in repo.")
        if st.button("Close"): st.session_state.articles_open=False

# ---------- Email explanation (before first success) ----------
with st.expander("Why do we ask for your email? / لماذا نطلب بريدك؟", expanded=not st.session_state.free_search_used):
    st.markdown(
        "- **EN:** We pass your email only as a `mailto` to OpenAlex so **you** get a fair, stable quota. "
        "We do not share it publicly or use it for marketing.  \n"
        "- **AR:** نستخدم بريدك فقط كقيمة `mailto` لدى OpenAlex لمنحك **حصّة مستقرة** وعادلة. "
        "لن يُنشر بريدك علنًا ولن نستخدمه للتسويق.  \n\n"
        "[OpenAlex: Rate limits & mailto](https://docs.openalex.org/how-to-use-the-api/rate-limits-and-mailto)"
    )

# ---------- Search box ----------
email_input = st.text_input("Email (recommended after first success) / البريد (مستحسن بعد أول نجاح)",
                            value=st.session_state.user_email, placeholder="name@example.com")
if email_input and valid_email(email_input): st.session_state.user_email = email_input.strip()

q = st.text_input("Search keyword… / اكتب كلمتك المفتاحية…")

def can_search_now():
    if st.session_state.user_email: return True
    if not st.session_state.free_search_used: return True
    return False

# ---------- Search (25) ----------
if st.button("🔎 Search / ابحث"):
    if not q.strip():
        st.warning("اكتب كلمة بحث أولًا / Please type a query.")
    elif not can_search_now():
        st.info("بعد أول نتيجة ناجحة يطلب النظام بريدك لضمان حصتك المستقرة. "
                "فضلاً أدخل بريدك أعلاه. / Email is required after the first successful search.")
    else:
        params = {"q": q, "per_page": 25}
        if st.session_state.user_email: params["user_mailto"] = st.session_state.user_email
        r = requests.get(f"{BACKEND_URL}/v1/search", params=params, timeout=30)
        if r.ok:
            data = r.json()
            if not st.session_state.user_email and not st.session_state.free_search_used:
                st.session_state.free_search_used = True
                st.success("🎉 تمّ نجاح أول نتيجة. للاستمرار بسلاسة، فضلاً أدخل بريدك (يُستخدم فقط كـ mailto).")
            render_results(data.get("results", []))
        else:
            if r.status_code==428:
                try:
                    info = r.json()
                    st.warning(info.get("detail",{}).get("hint_ar","Email required."))
                except Exception:
                    st.warning("Email required after first successful search.")
            else:
                st.error(f"API error {r.status_code}: {r.text}")

# ---------- Fetch 2000 & Download ----------
if st.button("⬇ Fetch up to 2000 & Download Excel"):
    if not can_search_now():
        st.info("Email is required after first success. / مطلوب بريدك بعد أول نجاح.")
    else:
        params = {"q": q or "", "target_count": 2000}
        if st.session_state.user_email: params["user_mailto"] = st.session_state.user_email
        r = requests.get(f"{BACKEND_URL}/v1/search_bulk", params=params, timeout=120)
        if r.ok:
            results = r.json().get("results", [])
            st.success(f"Fetched {len(results)} records.")
            df = to_dataframe(results)
            bio = io.BytesIO(); df.to_excel(bio, index=False, engine="openpyxl"); bio.seek(0)
            st.download_button("Download Excel (2000)", bio.getvalue(), file_name="results_2000.xlsx")
            render_results(results[:25])
        else:
            st.error(f"Error: {r.status_code} {r.text}")

# ---------- Owner override inside Egypt ----------
if st.session_state.get("country_code")=="EG" and not st.session_state.get("is_owner"):
    with st.expander("I’m the owner (unlock paid features on this device)"):
        email_o = st.selectbox("Choose verified email", [
            "doctormahmoud1984@gmail.com","yah20252025@gmail.com","drmahmoud@azhar.edu.eg"
        ])
        if st.button("Send OTP"): requests.post(f"{BACKEND_URL}/owner/init", data={"email": email_o}, timeout=10); st.info("OTP sent.")
        otp_o = st.text_input("Enter OTP")
        if st.button("Verify"):
            rr = requests.post(f"{BACKEND_URL}/owner/verify", data={"email": email_o, "otp": otp_o}, timeout=10)
            if rr.ok:
                st.session_state["is_owner"]=True
                st.session_state["show_paid_features"]=True
                st.success("Owner verified on this device.")
                st.rerun()

# ---------- Footer ----------
footer_identity()
