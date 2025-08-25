# -*- coding: utf-8 -*-
"""
Search It — Pro (Journal Rankings Enrichment)
---------------------------------------------
- جميع مزايا "Search It — Pro"
- إضافة دعم اختياري لدمج **تصنيفات المجلات** عبر ملف CSV يرفعه المستخدم
- مطابقة بالـ ISSN إن توفّر، وإلا مطابقة اسمية تقريبية باستخدام difflib (قياسي)
- عرض حقول: Quartile / SJR / ImpactFactor / SourceURL إن توفّرت

صيغة CSV المقترحة (عناوين الأعمدة المرنة التالية سيُحاول التطبيق اكتشافها تلقائيًا):
- Journal / Title
- ISSN / ISSNs (يدعم فواصل , أو ; أو |)
- Quartile / Q
- SJR
- ImpactFactor / IF / JIF
- SourceURL / URL
"""

import io
import os
import re
import json
import csv
import difflib
import requests
import pandas as pd
import streamlit as st

# ---------------- إعدادات ----------------
LANGS = [
    ("ar","العربية"),
    ("fa_AF","الأفغانية (داري/بشتو)"),
    ("en","English"),
    ("fr","Français"),
    ("de","Deutsch"),
    ("ru","Русский"),
    ("zh","中文"),
    ("es","Español"),
    ("tr","Türkçe"),
    ("fa","فارسی"),
]

DEFAULT_CONFIG = {
    "brand_title": "Search It — Pro",
    "openalex_base": "https://api.openalex.org/works",
    "openalex_mailto": "",
    "ui": {
        "lang": "ar",  # لغة الواجهة الافتراضية
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

st.set_page_config(page_title=CFG.get("brand_title","Search It — Pro"), page_icon="🔎", layout="wide")

# ---------------- ترجمات ----------------
T = {
    "title": {k: "Search It — Pro" for k,_ in LANGS},
    "search_placeholder": {
        "ar": "اكتب كلمتك المفتاحية…",
        "en": "Enter your keyword…",
        "fr": "Entrez votre mot-clé…",
        "de": "Suchbegriff eingeben…",
        "ru": "Введите ключевое слово…",
        "zh": "输入关键词…",
        "es": "Escribe tu palabra clave…",
        "tr": "Anahtar kelime girin…",
        "fa": "کلیدواژه خود را وارد کنید…",
        "fa_AF": "کلیدواژه را وارد کنید…",
    },
    "search_button": {k: "🔎 Search" for k,_ in LANGS},
    "adv_search": {k: "Advanced search" for k,_ in LANGS},
    "total_results": {k: "Total results (upstream)" for k,_ in LANGS},
    "displayed_after_filter": {k: "Displayed after local filtering" for k,_ in LANGS},
}
T["search_button"]["ar"] = "🔎 ابحث"
T["adv_search"]["ar"] = "البحث المتقدم"
T["total_results"]["ar"] = "إجمالي النتائج (من المصدر)"
T["displayed_after_filter"]["ar"] = "المعروضة بعد الفلترة المحلية"

def t(key, lang):
    return T.get(key, {}).get(lang, T.get(key, {}).get("en", key))

# ---------------- حالات الواجهة ----------------
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = CFG["ui"]["lang"]

# ---------------- رأس الصفحة واختيار اللغة ----------------
top_left, top_center, top_right = st.columns([1,2,1])
with top_center:
    st.markdown(f"<h2 style='text-align:center'>{t('title', st.session_state.ui_lang)}</h2>", unsafe_allow_html=True)
with top_right:
    st.session_state.ui_lang = st.selectbox("Language", [code for code,_ in LANGS],
        index=[code for code,_ in LANGS].index(st.session_state.ui_lang),
        format_func=lambda code: next((lbl for c,lbl in LANGS if c==code), code))

# ---------------- شريط البحث في الوسط ----------------
st.markdown("""
<style>
.center-box {max-width: 900px; margin: 0 auto; padding: 0.5rem 1rem; border-radius: 16px; background: #f8f9fb;}
</style>
""", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='center-box'>", unsafe_allow_html=True)
    q = st.text_input("", key="q_main", placeholder=t("search_placeholder", st.session_state.ui_lang), label_visibility="collapsed")
    cols = st.columns([6,2])
    with cols[0]:
        st.markdown("&nbsp;", unsafe_allow_html=True)
    with cols[1]:
        do_search = st.button(t("search_button", st.session_state.ui_lang))
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- البحث المتقدم ----------------
with st.expander(t("adv_search", st.session_state.ui_lang), expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        exact_phrase = st.text_input("العبارة الدقيقة", value="")
        any_words    = st.text_input("أيٌّ من هذه الكلمات (مفصولة بفواصل)", value="", placeholder="تعلم آلة, رؤية حاسوبية")
        none_words   = st.text_input("استثناء الكلمات", value="", placeholder="استعراض, مراجعة")
        lang_code    = st.selectbox("لغة النتائج", [c for c,_ in LANGS], index=[c for c,_ in LANGS].index(st.session_state.ui_lang))
    with c2:
        author       = st.text_input("اسم المؤلف", value="", placeholder="مثال: Andrew Ng")
        venue        = st.text_input("المجلة/المؤتمر", value="", placeholder="مثال: NeurIPS")
        doc_type     = st.multiselect("نوع الوثيقة", ["article","proceedings-article","book","monograph","dataset","dissertation","report","other"], default=[])
        open_access_only = st.checkbox("الوصول المفتوح فقط", value=False)
    with c3:
        years        = st.slider("المدى الزمني", 1990, 2030, (1990, 2030))
        sort_opt     = st.selectbox("الترتيب", ["الصلة (افتراضي)","الأحدث","الأكثر استشهادًا"], index=0)
        title_only   = st.checkbox("🔎 حصر النتائج على العنوان (title.search)", value=False)
        strict_local = st.checkbox("🧲 البحث الدلالي المحلي (تطابق ذكي)", value=True)

    st.markdown("---")
    st.subheader("تصنيفات المجلات (اختياري)")
    rank_file = st.file_uploader("ارفع ملف CSV يحوي تصنيفات المجلات (Journal, ISSN, Quartile, SJR, ImpactFactor, SourceURL)", type=["csv"])
    st.caption("سيتم المطابقة عبر ISSN أولًا، ثم مطابقة اسمية تقريبية إذا لم يتوفر ISSN. يدعم تعدد ISSN في الخلية الواحدة مفصولًا بـ , أو ; أو |")

    st.markdown("---")
    st.subheader("البحث الدلالي الخارجي (اختياري)")
    c4, c5, c6 = st.columns(3)
    with c4:
        semantic_provider = st.selectbox("المزوِّد", ["(غير مفعّل)","OpenAI","Cohere","Other"])
    with c5:
        semantic_api_key  = st.text_input("API Key", value="", type="password", placeholder="أدخل المفتاح هنا…")
    with c6:
        semantic_hint     = st.text_input("عنوان/نطاق دلالي (اختياري)", value="", placeholder="Topic embedding / مدلول عام…")
    st.caption("إن لم تضع API Key سيُستخدم البحث القياسي + الفلترة المحلية فقط.")

# ---------------- أدوات ----------------
def _ok(s): 
    return bool(re.search(r'[A-Za-z0-9\u0600-\u06FF]', (s or "")))

def _field(obj, path, default=None):
    cur = obj
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def _reconstruct_abstract(inv_index):
    if not inv_index or not isinstance(inv_index, dict):
        return ""
    pos_to_word = {}
    max_pos = -1
    for word, positions in inv_index.items():
        for p in positions:
            pos_to_word[p] = word
            max_pos = max(max_pos, p)
    return " ".join(pos_to_word.get(i, "") for i in range(max_pos+1)).strip() if max_pos >= 0 else ""

def _tokenize(text):
    if not text: return []
    return [t for t in re.split(r'[\s,;:،؛]+', text.strip()) if t]

def _apply_exclude(items, none_words):
    if not none_words: 
        return items
    excl = [x.strip().lower() for x in re.split(r'[,\s]+', none_words) if x.strip()]
    if not excl:
        return items
    filtered = []
    for w in items:
        title = (w.get("title") or "").lower()
        abstract = _reconstruct_abstract(_field(w, "abstract_inverted_index") or {}).lower()
        if any(x and ((x in title) or (x in abstract)) for x in excl):
            continue
        filtered.append(w)
    return filtered

def _apply_require(items, q, exact_phrase, any_words, enabled=True):
    if not enabled:
        return items
    req_tokens = []
    if q: req_tokens.extend(_tokenize(q))
    if exact_phrase: req_tokens.append(exact_phrase.strip())
    any_list = [w.strip() for w in any_words.split(",") if w.strip()] if any_words else []

    out = []
    for w in items:
        text = ((w.get("title") or "") + " " +
                _reconstruct_abstract(_field(w, "abstract_inverted_index") or ""))
        t = text.lower()
        ok_all = all(tok.lower() in t for tok in req_tokens) if req_tokens else True
        ok_any = any((aw.lower() in t) for aw in any_list) if any_list else True
        if ok_all and ok_any:
            out.append(w)
    return out

def _build_params(q, exact_phrase, any_words, author, venue, lang_code, years, open_access_only, doc_type, sort_opt, title_only):
    params, search_terms = {}, []
    if _ok(q):             search_terms.append(q.strip())
    if _ok(exact_phrase):  search_terms.append(f"\"{exact_phrase.strip()}\"")
    if any_words:
        terms = [w.strip() for w in any_words.split(",") if _ok(w)]
        if terms: search_terms.append(" OR ".join(terms))
    if search_terms:
        params["search"] = " ".join(search_terms)

    filters = []
    if _ok(author): filters.append(f"authorships.author.display_name.search:{author.strip()}")
    if _ok(venue):  filters.append(f"host_venue.display_name.search:{venue.strip()}")
    if lang_code:   filters.append(f"language:{lang_code}")
    if years and isinstance(years, (list, tuple)) and len(years) == 2:
        y0, y1 = years
        filters.append(f"from_publication_date:{y0}-01-01")
        filters.append(f"to_publication_date:{y1}-12-31")
    if open_access_only: filters.append("open_access.is_oa:true")
    if doc_type: filters.append(f"type:{'|'.join(doc_type)}")
    if title_only and _ok(q): filters.append(f"title.search:{q.strip()}")
    if filters: params["filter"] = ",".join(filters)

    if sort_opt == "الأحدث":            params["sort"] = "publication_date:desc"
    elif sort_opt == "الأكثر استشهادًا": params["sort"] = "cited_by_count:desc"
    else:                                params["sort"] = "relevance_score:desc"
    return params

def _request_openalex(url, params, headers):
    resp = requests.get(url, params=params, timeout=30, headers=headers)
    resp.raise_for_status()
    return resp

@st.cache_data(show_spinner=False)
def openalex_page(params, per_page=100, cursor="*"):
    base = CFG.get("openalex_base","https://api.openalex.org/works")
    mailto = (CFG.get("openalex_mailto") or os.environ.get("OPENALEX_MAILTO") or "").strip()
    headers = {"User-Agent": "SearchIt/Pro" + (f" (mailto:{mailto})" if mailto else "")}
    q = dict(params); q["per_page"] = per_page; q["cursor"] = cursor
    if mailto: q["mailto"] = mailto
    data = _request_openalex(base, q, headers).json()
    results = data.get("results", []) or []
    meta = data.get("meta", {}) or {}
    return results, meta.get("next_cursor"), meta.get("count", 0)

# ---------------- تحميل CSV للتصنيفات ----------------
def _norm_issn(s):
    return re.sub(r'[^0-9Xx]', '', (s or ''))

def _split_multi_issn(cell):
    if not cell: return []
    parts = re.split(r'[,\;\|]', str(cell))
    return [_norm_issn(p) for p in parts if _norm_issn(p)]

def _lower(s): return (s or "").strip().lower()

@st.cache_data(show_spinner=False)
def parse_rank_csv(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes))
    cols = {c.lower():c for c in df.columns}

    # مرونة أسماء الأعمدة
    jcol = cols.get("journal") or cols.get("title") or list(df.columns)[0]
    icol = cols.get("issn") or cols.get("issns") or None
    qcol = cols.get("quartile") or cols.get("q") or None
    scol = cols.get("sjr") or None
    icol2= cols.get("impactfactor") or cols.get("if") or cols.get("jif") or None
    ucol = cols.get("sourceurl") or cols.get("url") or None

    by_issn = {}
    by_name = {}

    for _, row in df.iterrows():
        name = str(row.get(jcol, "")).strip()
        entry = {
            "Journal": name or "",
            "Quartile": str(row.get(qcol, "") if qcol else ""),
            "SJR": str(row.get(scol, "") if scol else ""),
            "ImpactFactor": str(row.get(icol2, "") if icol2 else ""),
            "SourceURL": str(row.get(ucol, "") if ucol else ""),
        }
        if icol:
            issns = _split_multi_issn(row.get(icol))
            for issn in issns:
                by_issn[issn] = entry
        if name:
            by_name[_lower(name)] = entry
    return by_issn, by_name

def _match_ranking(venue_name, issn_list, by_issn, by_name):
    # أولوية للمطابقة عبر ISSN
    for issn in issn_list or []:
        key = _norm_issn(issn)
        if key and key in by_issn:
            return by_issn[key]

    # مطابقة اسمية تقريبية
    name = _lower(venue_name)
    if name in by_name:
        return by_name[name]
    # استخدم difflib للمطابقة التقريبية
    candidates = list(by_name.keys())
    if not candidates:
        return None
    best = difflib.get_close_matches(name, candidates, n=1, cutoff=0.9)
    if best:
        return by_name.get(best[0])
    return None

# ---------------- تنفيذ البحث ----------------
results = []
total_count = 0
ranking_bytes = None
if 'rank_file' in locals() and rank_file is not None:
    ranking_bytes = rank_file.read()

by_issn = {}
by_name = {}
if ranking_bytes:
    try:
        by_issn, by_name = parse_rank_csv(ranking_bytes)
        st.success(f"تم تحميل تصنيفات المجلات: {len(by_issn)} مدخل عبر ISSN، و {len(by_name)} عبر الاسم.")
    except Exception as e:
        st.error(f"تعذّر قراءة CSV: {e}")

if do_search and q.strip():
    params = _build_params(q, exact_phrase if 'exact_phrase' in locals() else "", any_words if 'any_words' in locals() else "",
                           author if 'author' in locals() else "", venue if 'venue' in locals() else "",
                           lang_code if 'lang_code' in locals() else "", 
                           years if 'years' in locals() else (1990,2030), 
                           open_access_only if 'open_access_only' in locals() else False, 
                           doc_type if 'doc_type' in locals() else [], 
                           sort_opt if 'sort_opt' in locals() else "الصلة (افتراضي)",
                           title_only if 'title_only' in locals() else False)
    try:
        results, next_cursor, total_count = openalex_page(params, per_page=100, cursor="*")
    except Exception as e:
        st.error(f"تعذّر الجلب من OpenAlex: {e}")
        results, next_cursor, total_count = [], None, 0

    # فلترة محلية ذكية (بحث دلالي محلي)
    strict_local_enabled = strict_local if 'strict_local' in locals() else True
    results = _apply_exclude(results, none_words if 'none_words' in locals() else "")
    results = _apply_require(results, q, exact_phrase if 'exact_phrase' in locals() else "", any_words if 'any_words' in locals() else "", enabled=strict_local_enabled)

# ---------------- عرض النتائج ----------------
if do_search and q.strip():
    st.success(f"{t('total_results', st.session_state.ui_lang)}: {total_count:,}")
    st.caption(f"{t('displayed_after_filter', st.session_state.ui_lang)}: {len(results):,}")
    if not results:
        st.info("لا توجد نتائج مطابقة. جرّب تقليل القيود أو إيقاف الفلترة المحلية.")
    else:
        for w in results:
            title = w.get("title") or "—"
            venue = _field(w,"host_venue.display_name") or _field(w,"primary_location.source.display_name") or "—"
            year  = _field(w,"publication_year") or "—"
            authors = ", ".join([_field(a,"author.display_name","") for a in (w.get("authorships") or []) if _field(a,"author.display_name")]) or "—"
            pdf   = _field(w, "open_access.oa_url") or _field(w, "primary_location.pdf_url")
            source= _field(w,"primary_location.source.url") or _field(w,"doi") or _field(w,"best_oa_location.url") or _field(w,"id")
            if source and isinstance(source, str) and source.startswith("10."):
                source = f"https://doi.org/{source}"
            cites = int(_field(w,"cited_by_count") or 0)

            # محاولة الحصول على ISSN من الكائن
            issns = []
            issn_l = _field(w, "host_venue.issn_l")
            if issn_l: issns.append(str(issn_l))
            issn_list = _field(w, "host_venue.issn")
            if isinstance(issn_list, list):
                issns.extend([str(x) for x in issn_list])

            rank_str = "—"
            if by_issn or by_name:
                match = _match_ranking(venue, issns, by_issn, by_name)
                if match:
                    parts = []
                    if match.get("Quartile"): parts.append(f"Q: {match['Quartile']}")
                    if match.get("SJR"): parts.append(f"SJR: {match['SJR']}")
                    if match.get("ImpactFactor"): parts.append(f"IF: {match['ImpactFactor']}")
                    if match.get("SourceURL"):
                        parts.append(f"<a href='{match['SourceURL']}' target='_blank'>المصدر</a>")
                    rank_str = " | ".join(parts) if parts else "—"

            st.markdown(f"### {title}")
            meta_line = f"🏷️ اسم المجلة: **{venue}**  •  👤 المؤلفون: **{authors}**  •  📅 العام: **{year}**  •  🏆 تصنيف المجلة: **{rank_str}**  •  📈 الاستشهادات: **{cites}**"
            st.caption(meta_line)

            actions = []
            if pdf: actions.append(f'<a href="{pdf}" target="_blank">⬇️ التحميل المباشر (PDF)</a>')
            if source: actions.append(f'<a href="{source}" target="_blank">⬇️ التحميل من المصدر</a>')
            actions.append('<a href="mailto:?subject=استفسار عن إحصاءات البحث">📊 لدي استفسار عن إحصاءات البحث</a>')
            actions.append('<a href="mailto:?subject=استفسار عن منهجية البحث">🧪 لدي استفسار عن منهجية البحث ونتائجها</a>')
            actions.append('<a href="mailto:?subject=خدمة التحليل الإحصائي">🧮 أرغب في خدمة التحليل الإحصائي</a>')
            actions.append('<a href="https://wa.me/201007975534" target="_blank">📞 تواصل معنا لطلب استشارة بحثية (واتساب)</a>')
            st.markdown(" | ".join(actions), unsafe_allow_html=True)
            st.markdown("---")
else:
    st.info("اكتب كلمتك ثم اضغط زر البحث (🔎 ابحث) لبدء الاستعلام. استخدم \"البحث المتقدم\" لضبط النتائج.")
