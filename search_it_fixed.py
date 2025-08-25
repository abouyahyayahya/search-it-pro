# -*- coding: utf-8 -*-
"""
Search It — OpenAlex (Fixed Version)
------------------------------------
- إزالة الاعتماد على searchh_complete_plus.py الذي كان يسبب توقف التطبيق.
- تحسين التحمل للأخطاء ورسائل الخطأ.
- دعم تصدير Excel مع محرك احتياطي (xlsxwriter أو openpyxl).
- إصلاح زر "التالي" لاستخدام st.rerun عند توافره.
- تحسين فلترة "استثناء الكلمات" على العنوان والملخّص.
- تحسين واجهة العرض لأزرار التحميل/المصدر/الإستشهادات.
"""

import io
import os
import re
import json
import math
import requests
import pandas as pd
import streamlit as st

# ---------------- إعدادات افتراضية/تحميل إعدادات ----------------
DEFAULT_CONFIG = {
    "brand_title": "Search It",
    "use_openalex": True,
    "openalex_base": "https://api.openalex.org/works",
    "openalex_mailto": "",
    "ui": {
        "default_lang": "",  # بدون تقييد لغة افتراضياً
        "available_langs": [["","بدون تقييد"],["ar","العربية"],["en","English"],["fr","Français"],["zh","简体中文"]],
        "display_mode": "cards",
    },
    "filters": {"years_min": 1990, "years_max": 2030, "open_access_only": False}
}

def _merge_dicts(base, other):
    out = dict(base)
    for k, v in other.items():
        if isinstance(v, dict) and k in out and isinstance(out[k], dict):
            out[k] = _merge_dicts(out[k], v)
        else:
            out[k] = v
    return out

def load_config():
    for name in ("config_search_it.json", "config_searche_today.json"):
        p = os.path.join(os.getcwd(), name)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    return _merge_dicts(DEFAULT_CONFIG, user_cfg)
            except Exception:
                pass
    return DEFAULT_CONFIG

CFG = load_config()

st.set_page_config(page_title=CFG.get("brand_title","Search It"), page_icon="🔎", layout="wide")
st.title(CFG.get("brand_title","Search It"))

# ---------------- أدوات OpenAlex ----------------
def _request_openalex(url, params, headers):
    try:
        resp = requests.get(url, params=params, timeout=30, headers=headers)
    except requests.RequestException as e:
        st.error(f"تعذّر الاتصال بـ OpenAlex: {e}")
        raise
    if not resp.ok:
        try:
            j = resp.json()
            err = j.get("error") or j.get("message") or resp.text
        except Exception:
            err = resp.text
        st.error(f"خطأ OpenAlex: {err}")
        resp.raise_for_status()
    return resp

@st.cache_data(show_spinner=False)
def openalex_page(params, per_page=100, cursor="*"):
    base = CFG.get("openalex_base","https://api.openalex.org/works")
    mailto = (CFG.get("openalex_mailto") or os.environ.get("OPENALEX_MAILTO") or "").strip()
    headers = {"User-Agent": "SearchIt/1.0" + (f" (mailto:{mailto})" if mailto else "")}
    q = dict(params); q["per_page"] = per_page; q["cursor"] = cursor
    if mailto: q["mailto"] = mailto
    data = _request_openalex(base, q, headers).json()
    results = data.get("results", []) or []
    meta = data.get("meta", {}) or {}
    return results, meta.get("next_cursor"), meta.get("count", 0)

def _ok(s): 
    return bool(re.search(r'[A-Za-z0-9\u0600-\u06FF]', (s or "")))

def build_query(query, exact_phrase, any_words, author, venue, lang_code, years, open_access_only, doc_type, sort_opt):
    params, search_terms = {}, []

    if _ok(query):        search_terms.append(query.strip())
    if _ok(exact_phrase): search_terms.append(f"\"{exact_phrase.strip()}\"")
    if any_words:
        # كلمات مفصولة بفواصل
        terms = [w.strip() for w in any_words.split(",") if _ok(w)]
        if terms: search_terms.append(" OR ".join(terms))
    if search_terms:
        params["search"] = " ".join(search_terms)

    filters = []
    if _ok(author): filters.append(f"authorships.author.display_name.search:{author.strip()}")
    if _ok(venue):  filters.append(f"host_venue.display_name.search:{venue.strip()}")
    if lang_code:   filters.append(f"language:{lang_code}")  # فارغ = بدون تقييد
    if years and isinstance(years, (list, tuple)) and len(years) == 2:
        y0, y1 = years
        filters.append(f"from_publication_date:{y0}-01-01")
        filters.append(f"to_publication_date:{y1}-12-31")
    if open_access_only: filters.append("open_access.is_oa:true")
    if doc_type: filters.append(f"type:{'|'.join(doc_type)}")
    if filters: params["filter"] = ",".join(filters)

    if sort_opt == "الأحدث":            params["sort"] = "publication_date:desc"
    elif sort_opt == "الأكثر استشهادًا": params["sort"] = "cited_by_count:desc"
    else:                                params["sort"] = "relevance_score:desc"
    return params

# ---------------- واجهة جانبية ----------------
defaults = {
    "q": "", "exact_phrase": "", "any_words": "", "none_words": "",
    "author": "", "venue": "", "lang_code": CFG["ui"]["default_lang"],
    "years": (CFG["filters"]["years_min"], CFG["filters"]["years_max"]),
    "doc_type": [], "open_access_only": False, "sort_opt": "الصلة (افتراضي)"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

with st.sidebar:
    st.subheader("إعدادات البحث")
    st.session_state.q            = st.text_input("الكلمات المفتاحية", value=st.session_state.q, placeholder="اكتب كلمتك…")
    st.session_state.exact_phrase = st.text_input("العبارة الدقيقة", value=st.session_state.exact_phrase)
    st.session_state.any_words    = st.text_input("أيٌّ من هذه الكلمات", value=st.session_state.any_words, placeholder="تعلم آلة, رؤية حاسوبية")
    st.session_state.none_words   = st.text_input("استثناء الكلمات", value=st.session_state.none_words, placeholder="استعراض, مراجعة")
    st.session_state.author       = st.text_input("اسم المؤلف", value=st.session_state.author, placeholder="مثال: Andrew Ng")
    st.session_state.venue        = st.text_input("المجلة/المؤتمر", value=st.session_state.venue, placeholder="مثال: NeurIPS")
    st.session_state.lang_code    = st.selectbox(
        "لغة النتائج",
        [code for code,_ in CFG["ui"]["available_langs"]],
        index=0,
        format_func=lambda code: next((lbl for c,lbl in CFG["ui"]["available_langs"] if c==code), code)
    )
    st.session_state.years        = st.slider("المدى الزمني", 1990, 2030, st.session_state.years)
    st.session_state.doc_type     = st.multiselect("نوع الوثيقة", ["article","proceedings-article","book","monograph","dataset","dissertation","report","other"], default=st.session_state.doc_type)
    st.session_state.open_access_only = st.checkbox("الوصول المفتوح فقط", value=st.session_state.open_access_only)
    st.session_state.sort_opt     = st.selectbox("الترتيب", ["الصلة (افتراضي)","الأحدث","الأكثر استشهادًا"], index=["الصلة (افتراضي)","الأحدث","الأكثر استشهادًا"].index(st.session_state.sort_opt))

# ---------------- إدارة الحالة وإطلاق الجلب ----------------
if "last_signature" not in st.session_state:
    st.session_state.last_signature = None
if "cursor" not in st.session_state:
    st.session_state.cursor = None
if "results" not in st.session_state:
    st.session_state.results = []
if "total_count" not in st.session_state:
    st.session_state.total_count = 0
if "last_params" not in st.session_state:
    st.session_state.last_params = None

signature = (
    st.session_state.q.strip(),
    st.session_state.exact_phrase.strip(),
    st.session_state.any_words.strip(),
    st.session_state.none_words.strip(),
    st.session_state.author.strip(),
    st.session_state.venue.strip(),
    st.session_state.lang_code,
    st.session_state.years,
    tuple(st.session_state.doc_type),
    st.session_state.open_access_only,
    st.session_state.sort_opt
)

if signature != st.session_state.last_signature and st.session_state.q.strip():
    st.session_state.last_signature = signature
    st.session_state.cursor = "*"
    st.session_state.results = []
    params = build_query(
        st.session_state.q, st.session_state.exact_phrase, st.session_state.any_words,
        st.session_state.author, st.session_state.venue, st.session_state.lang_code,
        st.session_state.years, st.session_state.open_access_only, st.session_state.doc_type,
        st.session_state.sort_opt
    )
    st.session_state.last_params = (params, st.session_state.none_words)

# ---------------- الدوال المساعدة للعرض والفلترة ----------------
def _field(obj, path, default=None):
    cur = obj
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def _build_pdf_and_source_urls(w):
    pdf_url   = _field(w, "open_access.oa_url") or _field(w, "primary_location.pdf_url")
    source_url= _field(w,"primary_location.source.url") or _field(w,"doi") or _field(w,"best_oa_location.url") or _field(w,"id")
    if source_url and isinstance(source_url, str) and source_url.startswith("10."):
        source_url = f"https://doi.org/{source_url}"
    return pdf_url, source_url

def _reconstruct_abstract(inv_index):
    """OpenAlex يعيد abstract_inverted_index كقائمة مقلوبة؛ نعيد بناء الملخص كنص."""
    if not inv_index or not isinstance(inv_index, dict):
        return ""
    pos_to_word = {}
    max_pos = 0
    for word, positions in inv_index.items():
        for p in positions:
            pos_to_word[p] = word
            if p > max_pos: max_pos = p
    return " ".join(pos_to_word.get(i, "") for i in range(max_pos+1)).strip()

def _apply_exclude(items, none_words):
    if not none_words: 
        return items
    excl = [x.strip().lower() for x in none_words.split(",") if x.strip()]
    if not excl:
        return items
    filtered = []
    for w in items:
        title = (w.get("title") or "").lower()
        abstract = _reconstruct_abstract(_field(w, "abstract_inverted_index") or {}).lower()
        # استبعد إن وُجدت أي كلمة محظورة في العنوان أو الملخّص
        if any(x and ((x in title) or (x in abstract)) for x in excl):
            continue
        filtered.append(w)
    return filtered

def render_actions_row_custom(w, ui_lang, content_lang, q, exact_phrase, any_words, CFG):
    pdf_url, source_url = _build_pdf_and_source_urls(w)
    cited = int(_field(w,"cited_by_count") or 0)
    pieces = []
    if pdf_url:
        pieces.append(f'<a href="{pdf_url}" target="_blank">📄 PDF</a>')
    if source_url:
        pieces.append(f'<a href="{source_url}" target="_blank">🔗 المصدر</a>')
    pieces.append(f'📈 الاستشهادات: <b>{cited}</b>')
    return " | ".join(pieces)

# ---------------- جلب النتائج (صفحة واحدة في كل تشغيل) ----------------
if st.session_state.last_params and st.session_state.cursor:
    params, none_words = st.session_state.last_params
    page_results, next_cursor, total_count = openalex_page(params, per_page=100, cursor=st.session_state.cursor)
    st.session_state.total_count = total_count or st.session_state.total_count
    st.session_state.cursor = next_cursor  # None عند نهاية النتائج
    st.session_state.results.extend(page_results)

# ---------------- عدّاد أعلى الصفحة ----------------
if st.session_state.total_count:
    st.success(f"إجمالي النتائج: {st.session_state.total_count:,}")

# ---------------- العرض ----------------
shown = _apply_exclude(st.session_state.results, st.session_state.last_params[1] if st.session_state.last_params else "")
if shown:
    for w in shown:
        title = w.get("title") or "—"
        venue = _field(w,"host_venue.display_name") or _field(w,"primary_location.source.display_name") or "—"
        year  = _field(w,"publication_year") or "—"
        st.markdown(f"### {title}")
        st.caption(f"{venue} • {year}")
        actions_html = render_actions_row_custom(w, "ar", "ar", st.session_state.q, st.session_state.exact_phrase, st.session_state.any_words, CFG)
        st.markdown(f'<div class="actions">{actions_html}</div>', unsafe_allow_html=True)
        st.markdown("---")
else:
    st.info("اكتب كلمة بحثك أو عدّل الإعدادات لبدء الجلب التلقائي…")

# ---------------- أسفل الصفحة: التالي + تنزيل Excel ----------------
col1, col2 = st.columns([1, 1])
with col1:
    if st.session_state.get("cursor"):
        if st.button("التالي ⏭️ (جلب 100 نتيجة إضافية)"):
            (getattr(st, "rerun", None) or st.experimental_rerun)()
    else:
        st.caption("لا توجد صفحات إضافية.")

with col2:
    if shown:
        rows = []
        for w in shown:
            pdf_url, source_url = _build_pdf_and_source_urls(w)
            rows.append({
                "Title": w.get("title",""),
                "Year": _field(w,"publication_year") or "",
                "Venue": _field(w,"host_venue.display_name") or _field(w,"primary_location.source.display_name") or "",
                "Citations": int(_field(w,"cited_by_count") or 0),
                "PDF": pdf_url or "",
                "Source": source_url or "",
            })
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        # محرك Excel احتياطي
        engine = "xlsxwriter"
        try:
            import xlsxwriter  # noqa: F401
        except Exception:
            engine = "openpyxl"
        with pd.ExcelWriter(buf, engine=engine) as writer:
            df.to_excel(writer, index=False, sheet_name="Results")
        st.download_button("⬇️ تحميل نتائج البحث (Excel)", data=buf.getvalue(),
                           file_name="search_results.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------- إرشادات ----------------
with st.expander("نصائح واستكشاف الأخطاء", expanded=False):
    st.markdown("""
- إن واجهت حدودًا في OpenAlex، أضف بريدًا إلى التهيئة `OPENALEX_MAILTO` لتحسين الحصص.
- جرّب تغيير "الترتيب" إلى "الأحدث" أو "الأكثر استشهادًا" حسب الحاجة.
- استخدم "استثناء الكلمات" لحذف موضوعات لا ترغب بها من العنوان أو الملخص.
""")
