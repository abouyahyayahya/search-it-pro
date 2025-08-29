# -*- coding: utf-8 -*-
"""
Search It — Pro (i18n Actions)
------------------------------
- ترجمة كل الأزرار/الأيقونات إلى 10 لغات (تتبدل ديناميكيًا مع اختيار لغة الواجهة).
- ربط جميع الأيقونات الخدمية برابط واتساب موحّد: 00201007975534
- تحسين بناء نص الرسالة تلقائيًا بحسب لغة الواجهة وعنوان العمل.
"""

import io
import os
import re
import json
import requests
import pandas as pd
import streamlit as st
from urllib.parse import quote

# ---------------- إعدادات عامّة ----------------
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
    "ui": {"lang": "ar"},
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
# مفاتيح قابلة لإعادة الاستخدام في الواجهة والأزرار
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
    # تسميات الأيقونات الخدمية
    "icon_download_pdf": {k: "⬇️ Download (PDF)" for k,_ in LANGS},
    "icon_download_source": {k: "⬇️ Download from source" for k,_ in LANGS},
    "icon_stats_q": {k: "📊 I have a question about research statistics" for k,_ in LANGS},
    "icon_method_q": {k: "🧪 I have a question about methodology & results" for k,_ in LANGS},
    "icon_analysis_service": {k: "🧮 I want statistical analysis service" for k,_ in LANGS},
    "icon_whatsapp": {k: "📞 Contact us for a research consultation (WhatsApp)" for k,_ in LANGS},
    # حقول الميتاداتا
    "meta_venue": {k: "Journal" for k,_ in LANGS},
    "meta_authors": {k: "Authors" for k,_ in LANGS},
    "meta_year": {k: "Year" for k,_ in LANGS},
    "meta_citations": {k: "Citations" for k,_ in LANGS},
}
# العربية
T["search_button"]["ar"] = "🔎 ابحث"
T["adv_search"]["ar"] = "البحث المتقدم"
T["total_results"]["ar"] = "إجمالي النتائج (من المصدر)"
T["displayed_after_filter"]["ar"] = "المعروضة بعد الفلترة المحلية"
T["icon_download_pdf"]["ar"] = "⬇️ التحميل المباشر (PDF)"
T["icon_download_source"]["ar"] = "⬇️ التحميل من المصدر"
T["icon_stats_q"]["ar"] = "📊 لدي استفسار عن إحصاءات البحث"
T["icon_method_q"]["ar"] = "🧪 لدي استفسار عن منهجية البحث ونتائجها"
T["icon_analysis_service"]["ar"] = "🧮 أرغب في خدمة التحليل الإحصائي"
T["icon_whatsapp"]["ar"] = "📞 تواصل معنا لطلب استشارة بحثية (واتساب)"
T["meta_venue"]["ar"] = "اسم المجلة"
T["meta_authors"]["ar"] = "المؤلفون"
T["meta_year"]["ar"] = "العام"
T["meta_citations"]["ar"] = "الاستشهادات"

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

# ---------------- أدوات طلب OpenAlex ----------------
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

# ---------------- تنفيذ البحث ----------------
results = []
total_count = 0
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
def _actions_row(lang, title, pdf, source):
    phone = "201007975534"  # بدون 00
    # رسالة مخصّصة حسب اللغة، نضيف عنوان العمل ليسهّل على الفريق معرفة السياق
    msg_stats = {
        "ar": f"لدي استفسار عن إحصاءات البحث بخصوص: {title}",
        "en": f"I have a question about research statistics for: {title}",
    }.get(lang, f"I have a question about research statistics for: {title}")
    msg_method = {
        "ar": f"لدي استفسار عن منهجية البحث ونتائجها بخصوص: {title}",
        "en": f"I have a question about research methodology & results for: {title}",
    }.get(lang, f"I have a question about research methodology & results for: {title}")
    msg_service = {
        "ar": f"أرغب في خدمة التحليل الإحصائي لبحث بعنوان: {title}",
        "en": f"I want a statistical analysis service for the paper: {title}",
    }.get(lang, f"I want a statistical analysis service for the paper: {title}")
    wa_stats = f"https://wa.me/{phone}?text={quote(msg_stats)}"
    wa_method = f"https://wa.me/{phone}?text={quote(msg_method)}"
    wa_service = f"https://wa.me/{phone}?text={quote(msg_service)}"
    wa_general = f"https://wa.me/{phone}?text={quote(title)}"
    parts = []
    if pdf:    parts.append(f'<a href="{pdf}" target="_blank">{t("icon_download_pdf", lang)}</a>')
    if source: parts.append(f'<a href="{source}" target="_blank">{t("icon_download_source", lang)}</a>')
    parts.append(f'<a href="{wa_stats}" target="_blank">{t("icon_stats_q", lang)}</a>')
    parts.append(f'<a href="{wa_method}" target="_blank">{t("icon_method_q", lang)}</a>')
    parts.append(f'<a href="{wa_service}" target="_blank">{t("icon_analysis_service", lang)}</a>')
    parts.append(f'<a href="{wa_general}" target="_blank">{t("icon_whatsapp", lang)}</a>')
    return " | ".join(parts)

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

            # سطر الميتاداتا مترجم
            meta = "  •  ".join([
                f"🏷️ {t('meta_venue', st.session_state.ui_lang)}: **{venue}**",
                f"👤 {t('meta_authors', st.session_state.ui_lang)}: **{authors}**",
                f"📅 {t('meta_year', st.session_state.ui_lang)}: **{year}**",
                f"📈 {t('meta_citations', st.session_state.ui_lang)}: **{cites}**",
            ])

            st.markdown(f"### {title}")
            st.caption(meta)
            st.markdown(_actions_row(st.session_state.ui_lang, title, pdf, source), unsafe_allow_html=True)
            st.markdown("---")
else:
    st.info("اكتب كلمتك ثم اضغط زر البحث (🔎 ابحث) لبدء الاستعلام. استخدم \"البحث المتقدم\" لضبط النتائج.")
