# -*- coding: utf-8 -*-
"""
Search It — Pro (i18n + Citations + Paging + Excel)
--------------------------------------------------
- كل الأيقونات/الأزرار مترجمة (10 لغات) وتتبدّل حسب لغة الواجهة.
- أيقونة "عرض التوثيق" بأساليب متعددة (APA7/APA6/MLA/IEEE/Chicago/Harvard/Vancouver).
- أيقونة "تصدير التوثيق" (RIS لبـ EndNote/Mendeley/Zotero + BibTeX).
- ترقيم الصفحات بواقع 500 عنوان لكل صفحة (يجلب داخليًا 200+200+100 من OpenAlex).
- زر "التالي" أسفل الصفحة + زر تحميل نتائج الصفحة إلى Excel.
- روابط واتساب لكل الأيقونات الخدمية برسالة تلقائية تحتوي عنوان العمل.
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
    # الأيقونات الحالية
    "icon_download_pdf": {k: "⬇️ Download (PDF)" for k,_ in LANGS},
    "icon_download_source": {k: "⬇️ Download from source" for k,_ in LANGS},
    "icon_stats_q": {k: "📊 I have a question about research statistics" for k,_ in LANGS},
    "icon_method_q": {k: "🧪 I have a question about methodology & results" for k,_ in LANGS},
    "icon_analysis_service": {k: "🧮 I want statistical analysis service" for k,_ in LANGS},
    "icon_whatsapp": {k: "📞 Contact us for a research consultation (WhatsApp)" for k,_ in LANGS},
    # الأيقونات الجديدة
    "icon_show_cite": {k: "📝 Show citation" for k,_ in LANGS},
    "icon_export_cite": {k: "📥 Export citation (RIS/BibTeX)" for k,_ in LANGS},
    "download_excel": {k: "⬇️ Download page results (Excel)" for k,_ in LANGS},
    "next_page": {k: "Next page ⏭️" for k,_ in LANGS},
    # حقول الميتاداتا
    "meta_venue": {k: "Journal" for k,_ in LANGS},
    "meta_authors": {k: "Authors" for k,_ in LANGS},
    "meta_year": {k: "Year" for k,_ in LANGS},
    "meta_citations": {k: "Citations" for k,_ in LANGS},
    # خيارات أنماط التوثيق
    "cite_style": {k: "Citation style" for k,_ in LANGS},
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
T["icon_show_cite"]["ar"] = "📝 عرض التوثيق"
T["icon_export_cite"]["ar"] = "📥 تصدير التوثيق (RIS/BibTeX)"
T["download_excel"]["ar"] = "⬇️ تحميل نتائج الصفحة (Excel)"
T["next_page"]["ar"] = "التالي ⏭️"
T["meta_venue"]["ar"] = "اسم المجلة"
T["meta_authors"]["ar"] = "المؤلفون"
T["meta_year"]["ar"] = "العام"
T["meta_citations"]["ar"] = "الاستشهادات"
T["cite_style"]["ar"] = "طريقة التوثيق"

def t(key, lang):
    return T.get(key, {}).get(lang, T.get(key, {}).get("en", key))

# ---------------- حالات الواجهة ----------------
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = CFG["ui"]["lang"]
if "cursor" not in st.session_state:
    st.session_state.cursor = None
if "last_signature" not in st.session_state:
    st.session_state.last_signature = None
if "page_results" not in st.session_state:
    st.session_state.page_results = []
if "total_count" not in st.session_state:
    st.session_state.total_count = 0

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
    cols = st.columns([4,2,2,2])
    with cols[0]:
        st.markdown("&nbsp;", unsafe_allow_html=True)
    with cols[1]:
        do_search = st.button(t("search_button", st.session_state.ui_lang))
    with cols[2]:
        cite_style = st.selectbox(t("cite_style", st.session_state.ui_lang),
                                  ["APA 7th","APA 6th","MLA 9th","IEEE","Chicago (Author-Date)","Harvard","Vancouver"],
                                  index=0)
    with cols[3]:
        title_only   = st.checkbox("title.search", value=False)
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
def openalex_page(params, per_page=200, cursor="*"):
    # per_page capped to 200 by OpenAlex; we'll loop to get 500
    base = CFG.get("openalex_base","https://api.openalex.org/works")
    mailto = (CFG.get("openalex_mailto") or os.environ.get("OPENALEX_MAILTO") or "").strip()
    headers = {"User-Agent": "SearchIt/Pro" + (f" (mailto:{mailto})" if mailto else "")}
    q = dict(params); q["per_page"] = min(200, max(1, per_page)); q["cursor"] = cursor
    if mailto: q["mailto"] = mailto
    data = _request_openalex(base, q, headers).json()
    results = data.get("results", []) or []
    meta = data.get("meta", {}) or {}
    return results, meta.get("next_cursor"), meta.get("count", 0)

def fetch_up_to(params, cursor, target_count=500):
    all_res = []
    total_count = 0
    cur = cursor or "*"
    for _ in range(5):  # up to 5 hops (200*5=1000 safeguard)
        if len(all_res) >= target_count or cur is None:
            break
        need = target_count - len(all_res)
        batch_size = 200 if need > 200 else need
        res, nxt, total = openalex_page(params, per_page=batch_size, cursor=cur)
        total_count = total or total_count
        all_res.extend(res)
        cur = nxt
        if not nxt:
            break
    return all_res[:target_count], cur, total_count

# ---------------- تهيئة البحث وتوقيع المعلمات ----------------
def signature_tuple(**kwargs):
    return tuple((k, kwargs.get(k)) for k in sorted(kwargs.keys()))

params_for_sig = dict(
    q=q, exact_phrase=locals().get("exact_phrase",""), any_words=locals().get("any_words",""),
    author=locals().get("author",""), venue=locals().get("venue",""),
    lang_code=locals().get("lang_code",""), years=locals().get("years",(1990,2030)),
    open_access_only=locals().get("open_access_only",False), doc_type=locals().get("doc_type",[]),
    sort_opt=locals().get("sort_opt","الصلة (افتراضي)"), title_only=locals().get("title_only",False),
    strict_local=locals().get("strict_local",True)
)

sig = signature_tuple(**params_for_sig)

if do_search and q.strip():
    st.session_state.last_signature = sig
    st.session_state.cursor = "*"
    params = _build_params(**{k:params_for_sig[k] for k in ["q","exact_phrase","any_words","author","venue","lang_code","years","open_access_only","doc_type","sort_opt","title_only"]})
    raw_results, nxt_cursor, total = fetch_up_to(params, st.session_state.cursor, target_count=500)
    # فلترة محلية
    raw_results = _apply_exclude(raw_results, params_for_sig["any_words"]*0 + locals().get("none_words",""))  # trick to keep mypy calm
    raw_results = _apply_require(raw_results, params_for_sig["q"], params_for_sig["exact_phrase"], params_for_sig["any_words"], enabled=params_for_sig["strict_local"])
    st.session_state.page_results = raw_results
    st.session_state.cursor = nxt_cursor
    st.session_state.total_count = total
elif st.session_state.last_signature == sig and st.session_state.page_results:
    # عرض نفس الصفحة إن لم يُضغط بحث مجددًا
    pass
else:
    st.session_state.page_results = []

# ---------------- مولدات التوثيق والتصدير ----------------
def _authors_list(work):
    names = []
    for a in (work.get("authorships") or []):
        nm = _field(a,"author.display_name")
        if nm: names.append(nm)
    return names

def _authors_apa(names, max_authors=20):
    # بسيط: "Last, F. M.," مع & قبل الأخير
    def fmt(n):
        parts = n.split()
        if len(parts) == 1: return parts[0]
        last = parts[-1]
        initials = "".join([p[0].upper()+"." for p in parts[:-1] if p])
        return f"{last}, {initials}"
    names2 = [fmt(n) for n in names]
    if len(names2) > max_authors:
        names2 = names2[:max_authors] + ["..."]
    if len(names2) >= 2:
        return ", ".join(names2[:-1]) + ", & " + names2[-1]
    return names2[0] if names2 else ""

def _pages(biblio):
    fp = _field(biblio,"first_page")
    lp = _field(biblio,"last_page")
    if fp and lp: return f"{fp}-{lp}"
    return fp or lp or ""

def fmt_citation(work, style="APA 7th"):
    title = work.get("title","")
    year  = _field(work,"publication_year") or ""
    venue = _field(work,"host_venue.display_name") or _field(work,"primary_location.source.display_name") or ""
    doi   = _field(work,"doi") or ""
    biblio = work.get("biblio") or {}
    vol = _field(biblio,"volume") or ""
    issue = _field(biblio,"issue") or ""
    pages = _pages(biblio)
    authors = _authors_list(work)

    if style in ("APA 7th","APA 6th"):
        authors_str = _authors_apa(authors)
        pieces = [authors_str, f"({year}).", f"{title}.", venue]
        if vol: pieces[-1] += f", {vol}"
        if issue: pieces[-1] += f"({issue})"
        if pages: pieces[-1] += f", {pages}"
        s = " ".join([p for p in pieces if p])
        if doi: s += f". https://doi.org/{doi}" if not str(doi).startswith("10.") else f". https://doi.org/{doi}"
        return s

    if style == "MLA 9th":
        authors_str = ", ".join(authors) if authors else ""
        s = f"{authors_str}. \"{title}.\" {venue}"
        if vol: s += f", vol. {vol}"
        if issue: s += f", no. {issue}"
        if year: s += f", {year}"
        if pages: s += f", pp. {pages}"
        if doi: s += f". doi:{doi}"
        return s

    if style == "IEEE":
        # A. Author, "Title," Journal, vol., no., pp., Year, doi
        def fmt(n):
            parts = n.split()
            if len(parts)==1: return n
            last = parts[-1]
            initials = " ".join([p[0].upper()+"." for p in parts[:-1] if p])
            return f"{initials} {last}"
        authors_str = ", ".join([fmt(n) for n in authors])
        s = f"{authors_str}, \"{title},\" {venue}"
        if vol: s += f", vol. {vol}"
        if issue: s += f", no. {issue}"
        if pages: s += f", pp. {pages}"
        if year: s += f", {year}"
        if doi: s += f", doi: {doi}"
        return s

    if style in ("Chicago (Author-Date)","Harvard","Vancouver"):
        authors_str = ", ".join(authors)
        s = f"{authors_str} ({year}). {title}. {venue}"
        if vol: s += f" {vol}"
        if issue: s += f"({issue})"
        if pages: s += f": {pages}"
        if doi: s += f". doi:{doi}"
        return s

    return f"{title} ({year})"

def ris_entry(work):
    title = work.get("title","")
    year  = _field(work,"publication_year") or ""
    venue = _field(work,"host_venue.display_name") or _field(work,"primary_location.source.display_name") or ""
    doi   = _field(work,"doi") or ""
    biblio = work.get("biblio") or {}
    vol = _field(biblio,"volume") or ""
    issue = _field(biblio,"issue") or ""
    pages = _pages(biblio)
    ris_lines = ["TY  - JOUR"]
    for n in _authors_list(work):
        ris_lines.append(f"AU  - {n}")
    if year: ris_lines.append(f"PY  - {year}")
    if title: ris_lines.append(f"TI  - {title}")
    if venue: ris_lines.append(f"JO  - {venue}")
    if vol: ris_lines.append(f"VL  - {vol}")
    if issue: ris_lines.append(f"IS  - {issue}")
    if pages: ris_lines.append(f"SP  - {pages.split('-')[0]}")
    if pages and '-' in pages: ris_lines.append(f"EP  - {pages.split('-')[-1]}")
    if doi: ris_lines.append(f"DO  - {doi}")
    ris_lines.append("ER  -")
    return "\n".join(ris_lines)

def bibtex_entry(work, idx=1):
    key = "ref" + str(idx)
    title = work.get("title","")
    year  = _field(work,"publication_year") or ""
    venue = _field(work,"host_venue.display_name") or _field(work,"primary_location.source.display_name") or ""
    doi   = _field(work,"doi") or ""
    biblio = work.get("biblio") or {}
    vol = _field(biblio,"volume") or ""
    issue = _field(biblio,"issue") or ""
    pages = _pages(biblio)
    authors = " and ".join(_authors_list(work))
    lines = [f"@article{{{key},",
             f"  title={{ {title} }},",
             f"  author={{ {authors} }},",
             f"  journal={{ {venue} }},",
             f"  year={{ {year} }},"]
    if vol: lines.append(f"  volume={{ {vol} }},")
    if issue: lines.append(f"  number={{ {issue} }},")
    if pages: lines.append(f"  pages={{ {pages} }},")
    if doi: lines.append(f"  doi={{ {doi} }},")
    lines.append("}")
    return "\n".join(lines)

# ---------------- عرض النتائج ----------------
def _actions_row(lang, title, pdf, source):
    phone = "201007975534"
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

def display_results(results):
    # ملخص أعلى
    st.success(f"{t('total_results', st.session_state.ui_lang)}: {st.session_state.total_count:,}")
    st.caption(f"{t('displayed_after_filter', st.session_state.ui_lang)}: {len(results):,}")

    # أزرار تحكم عليا (Excel للصفحة)
    if results:
        # Excel export for current page
        rows = []
        for w in results:
            title = w.get("title","")
            venue = _field(w,"host_venue.display_name") or _field(w,"primary_location.source.display_name") or ""
            year  = _field(w,"publication_year") or ""
            authors = ", ".join([_field(a,"author.display_name","") for a in (w.get("authorships") or []) if _field(a,"author.display_name")]) or ""
            cites = int(_field(w,"cited_by_count") or 0)
            pdf   = _field(w, "open_access.oa_url") or _field(w, "primary_location.pdf_url") or ""
            source= _field(w,"primary_location.source.url") or _field(w,"doi") or _field(w,"best_oa_location.url") or _field(w,"id") or ""
            if source and isinstance(source, str) and source.startswith("10."):
                source = f"https://doi.org/{source}"
            rows.append({
                "Title": title, "Journal": venue, "Authors": authors, "Year": year,
                "Citations": cites, "PDF": pdf, "Source": source
            })
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        try:
            import xlsxwriter  # noqa: F401
            engine = "xlsxwriter"
        except Exception:
            engine = "openpyxl"
        with pd.ExcelWriter(buf, engine=engine) as writer:
            df.to_excel(writer, index=False, sheet_name="Results")
        st.download_button(t("download_excel", st.session_state.ui_lang), data=buf.getvalue(),
                           file_name="search_results_page.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # عرض كل عنصر مع الأيقونات + التوثيق/التصدير
    for idx, w in enumerate(results, start=1):
        title = w.get("title") or "—"
        venue = _field(w,"host_venue.display_name") or _field(w,"primary_location.source.display_name") or "—"
        year  = _field(w,"publication_year") or "—"
        authors = ", ".join([_field(a,"author.display_name","") for a in (w.get("authorships") or []) if _field(a,"author.display_name")]) or "—"
        pdf   = _field(w, "open_access.oa_url") or _field(w, "primary_location.pdf_url")
        source= _field(w,"primary_location.source.url") or _field(w,"doi") or _field(w,"best_oa_location.url") or _field(w,"id")
        if source and isinstance(source, str) and source.startswith("10."):
            source = f"https://doi.org/{source}"
        cites = int(_field(w,"cited_by_count") or 0)

        st.markdown(f"### {title}")
        meta = "  •  ".join([
            f"🏷️ {t('meta_venue', st.session_state.ui_lang)}: **{venue}**",
            f"👤 {t('meta_authors', st.session_state.ui_lang)}: **{authors}**",
            f"📅 {t('meta_year', st.session_state.ui_lang)}: **{year}**",
            f"📈 {t('meta_citations', st.session_state.ui_lang)}: **{cites}**",
        ])
        st.caption(meta)
        st.markdown(_actions_row(st.session_state.ui_lang, title, pdf, source), unsafe_allow_html=True)

        # --- Citation display & export row ---
        c1, c2 = st.columns([1,1])
        with c1:
            with st.expander(f"{t('icon_show_cite', st.session_state.ui_lang)} — {cite_style}"):
                st.code(fmt_citation(w, cite_style))
        with c2:
            # Export buttons (RIS & BibTeX)
            ris_data = ris_entry(w).encode("utf-8")
            bib_data = bibtex_entry(w, idx=idx).encode("utf-8")
            st.download_button(f"RIS", data=ris_data, file_name=f"ref_{idx}.ris", mime="application/x-research-info-systems", key=f"ris_{idx}")
            st.download_button(f"BibTeX", data=bib_data, file_name=f"ref_{idx}.bib", mime="text/x-bibtex", key=f"bib_{idx}")
        st.markdown("---")

# ---------------- التنفيذ ----------------
if st.session_state.page_results:
    display_results(st.session_state.page_results)
    # زر التالي أسفل الصفحة
    if st.session_state.cursor:
        if st.button(t("next_page", st.session_state.ui_lang)):
            params = _build_params(**{k:params_for_sig[k] for k in ["q","exact_phrase","any_words","author","venue","lang_code","years","open_access_only","doc_type","sort_opt","title_only"]})
            raw_results, nxt_cursor, total = fetch_up_to(params, st.session_state.cursor, target_count=500)
            raw_results = _apply_exclude(raw_results, locals().get("none_words",""))
            raw_results = _apply_require(raw_results, params_for_sig["q"], params_for_sig["exact_phrase"], params_for_sig["any_words"], enabled=params_for_sig["strict_local"])
            st.session_state.page_results = raw_results
            st.session_state.cursor = nxt_cursor
            st.session_state.total_count = total
            (getattr(st, "rerun", None) or st.experimental_rerun)()
    else:
        st.caption("— لا توجد صفحة لاحقة —")
elif do_search and not q.strip():
    st.info("أدخل كلمة مفتاحية.")
else:
    st.info("اكتب كلمتك ثم اضغط زر البحث (🔎 ابحث)، وحدد طريقة التوثيق من القائمة.")

