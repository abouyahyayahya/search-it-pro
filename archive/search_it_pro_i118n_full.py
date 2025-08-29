# -*- coding: utf-8 -*-
"""
Search It — Pro (Full)
======================

Features:
- Full i18n (10 UI languages) affecting ALL labels, including action icons.
- Centered search bar with 🔎 button + "Citation style" selector + title.search.
- "Advanced search" with recommended filters.
- Results paging: 500 items per page (iterative calls to OpenAlex).
- Per-item actions row: Download PDF/source + 4 WhatsApp actions (localized) with prefilled messages.
- Per-item citation display (APA7/APA6/MLA/IEEE/Chicago/Harvard/Vancouver) + export RIS/BibTeX.
- Page-level Excel export for currently shown 500 results.
- Local semantic filter (smart match on title+abstract). 
- Optional external semantic provider/API key fields (placeholders).
"""

import io, os, re, json, requests, pandas as pd, streamlit as st
from urllib.parse import quote

# ---------------- UI languages ----------------
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

# ---------------- Translations (base EN + AR/FR overrides) ----------------
def make_T():
    base = {
        "app_title": "Search It — Pro",
        "lang_label": "Language",
        "search_placeholder": "Enter your keyword…",
        "search_btn": "🔎 Search",
        "cite_style": "Citation style",
        "title_only": "title.search",
        "adv_search": "Advanced search",
        "exact_phrase": "Exact phrase",
        "any_words": "Any of these words (comma-separated)",
        "none_words": "Exclude words",
        "author": "Author name",
        "venue": "Journal/Conference",
        "result_lang": "Result language",
        "doc_type": "Document type",
        "oa_only": "Open access only",
        "years": "Year range",
        "sort": "Sort by",
        "sort_rel": "Relevance (default)",
        "sort_new": "Newest",
        "sort_cited": "Most cited",
        "strict_local": "Semantic local filter (smart match)",
        "semantic_ext": "External semantic search (optional)",
        "provider": "Provider",
        "api_key": "API Key",
        "topic_hint": "Topic/hint (optional)",
        "note_semantic": "If no API key is provided, the app uses standard OpenAlex search with local semantic filtering only.",
        "total_results": "Total results (upstream)",
        "shown_after": "Displayed after local filtering",
        "meta_venue": "Journal",
        "meta_authors": "Authors",
        "meta_year": "Year",
        "meta_citations": "Citations",
        "dl_pdf": "⬇️ Download (PDF)",
        "dl_src": "⬇️ Download from source",
        "q_stats": "📊 I have a question about research statistics",
        "q_method": "🧪 I have a question about methodology & results",
        "q_service": "🧮 I want statistical analysis service",
        "q_whatsapp": "📞 Contact us for a research consultation (WhatsApp)",
        "download_excel": "⬇️ Download page results (Excel)",
        "next_page": "Next page ⏭️",
        "no_more_pages": "— No next page —",
        "enter_keyword": "Type your keyword then click Search.",
    }
    T = {code: dict(base) for code,_ in LANGS}

    # Arabic
    T["ar"].update({
        "lang_label": "اللغة",
        "search_placeholder": "اكتب كلمتك المفتاحية…",
        "search_btn": "🔎 ابحث",
        "cite_style": "طريقة التوثيق",
        "title_only": "حصر النتائج على العنوان (title.search)",
        "adv_search": "البحث المتقدم",
        "exact_phrase": "العبارة الدقيقة",
        "any_words": "أيٌّ من هذه الكلمات (مفصولة بفواصل)",
        "none_words": "استثناء الكلمات",
        "author": "اسم المؤلف",
        "venue": "المجلة/المؤتمر",
        "result_lang": "لغة النتائج",
        "doc_type": "نوع الوثيقة",
        "oa_only": "الوصول المفتوح فقط",
        "years": "المدى الزمني",
        "sort": "الترتيب",
        "sort_rel": "الصلة (افتراضي)",
        "sort_new": "الأحدث",
        "sort_cited": "الأكثر استشهادًا",
        "strict_local": "البحث الدلالي المحلي (تطابق ذكي)",
        "semantic_ext": "البحث الدلالي الخارجي (اختياري)",
        "provider": "المزوِّد",
        "api_key": "مفتاح API",
        "topic_hint": "عنوان/نطاق دلالي (اختياري)",
        "note_semantic": "إذا لم تضع مفتاح API فسيُستخدم بحث OpenAlex القياسي + الفلترة الدلالية المحلية فقط.",
        "total_results": "إجمالي النتائج (من المصدر)",
        "shown_after": "المعروضة بعد الفلترة المحلية",
        "meta_venue": "اسم المجلة",
        "meta_authors": "المؤلفون",
        "meta_year": "العام",
        "meta_citations": "الاستشهادات",
        "dl_pdf": "⬇️ التحميل المباشر (PDF)",
        "dl_src": "⬇️ التحميل من المصدر",
        "q_stats": "📊 لدي استفسار عن إحصاءات البحث",
        "q_method": "🧪 لدي استفسار عن منهجية البحث ونتائجها",
        "q_service": "🧮 أرغب في خدمة التحليل الإحصائي",
        "q_whatsapp": "📞 تواصل معنا لطلب استشارة بحثية (واتساب)",
        "download_excel": "⬇️ تحميل نتائج الصفحة (Excel)",
        "next_page": "التالي ⏭️",
        "no_more_pages": "— لا توجد صفحة لاحقة —",
        "enter_keyword": "اكتب كلمتك ثم اضغط زر ابحث.",
    })

    # French
    T["fr"].update({
        "lang_label": "Langue",
        "search_placeholder": "Entrez votre mot-clé…",
        "search_btn": "🔎 Rechercher",
        "cite_style": "Style de citation",
        "title_only": "title.search",
        "adv_search": "Recherche avancée",
        "exact_phrase": "Expression exacte",
        "any_words": "N’importe lequel de ces mots (séparés par des virgules)",
        "none_words": "Exclure des mots",
        "author": "Auteur",
        "venue": "Revue/Conférence",
        "result_lang": "Langue des résultats",
        "doc_type": "Type de document",
        "oa_only": "Accès libre uniquement",
        "years": "Plage d’années",
        "sort": "Trier par",
        "sort_rel": "Pertinence (par défaut)",
        "sort_new": "Plus récent",
        "sort_cited": "Le plus cité",
        "strict_local": "Filtre sémantique local (pertinence intelligente)",
        "semantic_ext": "Recherche sémantique externe (optionnelle)",
        "provider": "Fournisseur",
        "api_key": "Clé API",
        "topic_hint": "Sujet/indice (optionnel)",
        "note_semantic": "Sans clé API, seule la recherche OpenAlex + filtrage local est utilisée.",
        "total_results": "Résultats totaux (source)",
        "shown_after": "Affichés après filtrage local",
        "meta_venue": "Revue",
        "meta_authors": "Auteurs",
        "meta_year": "Année",
        "meta_citations": "Citations",
        "dl_pdf": "⬇️ Télécharger (PDF)",
        "dl_src": "⬇️ Télécharger depuis la source",
        "q_stats": "📊 J’ai une question sur les statistiques de recherche",
        "q_method": "🧪 J’ai une question sur la méthodologie et les résultats",
        "q_service": "🧮 Je souhaite un service d’analyse statistique",
        "q_whatsapp": "📞 Nous contacter pour une consultation (WhatsApp)",
        "download_excel": "⬇️ Télécharger les résultats de la page (Excel)",
        "next_page": "Page suivante ⏭️",
        "no_more_pages": "— Pas de page suivante —",
        "enter_keyword": "Saisissez un mot-clé puis cliquez sur Rechercher.",
    })
    return T

T = make_T()

def t(lang, key): return T.get(lang, T["en"]).get(key, T["en"].get(key, key))

# ---------------- App config / state ----------------
st.set_page_config(page_title="Search It — Pro", page_icon="🔎", layout="wide")

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "ar"  # default Arabic as requested
if "cursor" not in st.session_state:
    st.session_state.cursor = None
if "last_signature" not in st.session_state:
    st.session_state.last_signature = None
if "page_results" not in st.session_state:
    st.session_state.page_results = []
if "total_count" not in st.session_state:
    st.session_state.total_count = 0

# ---------------- Header (title + language) ----------------
left, mid, right = st.columns([1,2,1])
with mid:
    st.markdown(f"<h2 style='text-align:center'>{t(st.session_state.ui_lang,'app_title')}</h2>", unsafe_allow_html=True)
with right:
    new_lang = st.selectbox(t(st.session_state.ui_lang,'lang_label'), [c for c,_ in LANGS],
                            index=[c for c,_ in LANGS].index(st.session_state.ui_lang),
                            format_func=lambda code: dict(LANGS)[code])
    if new_lang != st.session_state.ui_lang:
        st.session_state.ui_lang = new_lang
        (getattr(st, "rerun", None) or st.experimental_rerun)()

# ---------------- Top search box ----------------
st.markdown("<div style='max-width:980px;margin:0 auto;padding:0.75rem 1rem;background:#f8f9fb;border-radius:16px'>", unsafe_allow_html=True)
q = st.text_input("", key="q_main", placeholder=t(st.session_state.ui_lang,'search_placeholder'), label_visibility="collapsed")
cols = st.columns([5,2,3,2])
with cols[0]: st.markdown("&nbsp;", unsafe_allow_html=True)
with cols[1]: do_search = st.button(t(st.session_state.ui_lang,'search_btn'))
with cols[2]:
    cite_style = st.selectbox(t(st.session_state.ui_lang,'cite_style'),
                              ["APA 7th","APA 6th","MLA 9th","IEEE","Chicago (Author-Date)","Harvard","Vancouver"], index=0)
with cols[3]:
    title_only = st.checkbox(t(st.session_state.ui_lang,'title_only'), value=False, key="title_only")
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Advanced search ----------------
with st.expander(t(st.session_state.ui_lang,'adv_search'), expanded=False):
    c1,c2,c3 = st.columns(3)
    with c1:
        exact_phrase = st.text_input(t(st.session_state.ui_lang,'exact_phrase'), value="")
        any_words    = st.text_input(t(st.session_state.ui_lang,'any_words'), value="", placeholder="ML, CV")
        none_words   = st.text_input(t(st.session_state.ui_lang,'none_words'), value="")
        # Result language filter (OpenAlex codes). Blank = no restriction
        result_lang = st.selectbox(t(st.session_state.ui_lang,'result_lang'),
                                   ["", "ar","en","fr","de","ru","zh","es","tr","fa"], index=0)
    with c2:
        author       = st.text_input(t(st.session_state.ui_lang,'author'), value="")
        venue        = st.text_input(t(st.session_state.ui_lang,'venue'), value="")
        doc_type     = st.multiselect(t(st.session_state.ui_lang,'doc_type'),
                        ["article","proceedings-article","book","monograph","dataset","dissertation","report","other"], default=[])
        open_access_only = st.checkbox(t(st.session_state.ui_lang,'oa_only'), value=False)
    with c3:
        years        = st.slider(t(st.session_state.ui_lang,'years'), 1990, 2030, (1990, 2030))
        sort_opt     = st.selectbox(t(st.session_state.ui_lang,'sort'),
                                    [t(st.session_state.ui_lang,'sort_rel'), t(st.session_state.ui_lang,'sort_new'), t(st.session_state.ui_lang,'sort_cited')], index=0)
        strict_local = st.checkbox(t(st.session_state.ui_lang,'strict_local'), value=True)

    st.markdown("---")
    st.subheader(t(st.session_state.ui_lang,'semantic_ext'))
    c4, c5, c6 = st.columns(3)
    with c4:
        provider = st.selectbox(t(st.session_state.ui_lang,'provider'), ["(disabled)","OpenAI","Cohere","Other"])
    with c5:
        api_key  = st.text_input(t(st.session_state.ui_lang,'api_key'), value="", type="password")
    with c6:
        topic_hint = st.text_input(t(st.session_state.ui_lang,'topic_hint'), value="")
    st.caption(t(st.session_state.ui_lang,'note_semantic'))

# ---------------- Helpers ----------------
def _field(o, path, d=None):
    cur = o
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return d
    return cur

def _reconstruct_abstract(inv_index):
    if not inv_index or not isinstance(inv_index, dict): return ""
    pos_to_word={}; mx=-1
    for w,positions in inv_index.items():
        for p in positions:
            pos_to_word[p]=w; mx=max(mx,p)
    return " ".join(pos_to_word.get(i,"") for i in range(mx+1)).strip() if mx>=0 else ""

def _ok(s): return bool(re.search(r'[A-Za-z0-9\u0600-\u06FF]', (s or "")))

def _tokenize(text):
    if not text: return []
    return [t for t in re.split(r'[\s,;:،؛]+', text.strip()) if t]

def _apply_exclude(items, none_words):
    if not none_words: return items
    excl = [x.strip().lower() for x in re.split(r'[,\s]+', none_words) if x.strip()]
    out = []
    for w in items:
        title = (w.get("title") or "").lower()
        abstract = _reconstruct_abstract(_field(w, "abstract_inverted_index") or {}).lower()
        if any(x and (x in title or x in abstract) for x in excl):
            continue
        out.append(w)
    return out

def _apply_require(items, q, exact_phrase, any_words, enabled=True):
    if not enabled: return items
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

def _build_params(q, exact_phrase, any_words, author, venue, result_lang, years, open_access_only, doc_type, sort_opt, title_only):
    params, search_terms = {}, []
    if _ok(q):             search_terms.append(q.strip())
    if _ok(exact_phrase):  search_terms.append(f"\"{exact_phrase.strip()}\"")
    if any_words:
        terms = [w.strip() for w in any_words.split(",") if _ok(w)]
        if terms: search_terms.append(" OR ".join(terms))
    if search_terms: params["search"] = " ".join(search_terms)

    # Sort mapping by localized label
    sort_map = {
        t(st.session_state.ui_lang,'sort_rel'): "relevance_score:desc",
        t(st.session_state.ui_lang,'sort_new'): "publication_date:desc",
        t(st.session_state.ui_lang,'sort_cited'): "cited_by_count:desc",
    }
    params["sort"] = sort_map.get(sort_opt, "relevance_score:desc")

    filters = []
    if _ok(author): filters.append(f"authorships.author.display_name.search:{author.strip()}")
    if _ok(venue):  filters.append(f"host_venue.display_name.search:{venue.strip()}")
    if result_lang: filters.append(f"language:{result_lang}")
    if years: filters += [f"from_publication_date:{years[0]}-01-01", f"to_publication_date:{years[1]}-12-31"]
    if open_access_only: filters.append("open_access.is_oa:true")
    if doc_type: filters.append(f"type:{'|'.join(doc_type)}")
    if title_only and _ok(q): filters.append(f"title.search:{q.strip()}")
    if filters: params["filter"] = ",".join(filters)
    return params

def _request_openalex(url, params, headers):
    r = requests.get(url, params=params, timeout=30, headers=headers)
    r.raise_for_status()
    return r

@st.cache_data(show_spinner=False)
def openalex_page(params, per_page=200, cursor="*"):
    # OpenAlex caps per_page at 200, so we chain calls in fetch_up_to
    base = "https://api.openalex.org/works"
    mailto = (os.environ.get("OPENALEX_MAILTO") or "").strip()
    headers = {"User-Agent": "SearchIt/ProFull" + (f" (mailto:{mailto})" if mailto else "")}
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
    for _ in range(5):  # up to 1000 items safety
        if len(all_res) >= target_count or cur is None:
            break
        need = target_count - len(all_res)
        batch = 200 if need > 200 else need
        res, nxt, total = openalex_page(params, per_page=batch, cursor=cur)
        total_count = total or total_count
        all_res.extend(res)
        cur = nxt
        if not nxt:
            break
    return all_res[:target_count], cur, total_count

# ---------------- Citation helpers ----------------
def _authors_list(work):
    names = []
    for a in (work.get("authorships") or []):
        nm = _field(a,"author.display_name")
        if nm: names.append(nm)
    return names

def _authors_apa(names, max_authors=20):
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

# ---------------- Actions row (WhatsApp + downloads) ----------------
def actions_row(lang, title, pdf, source):
    phone="201007975534"  # WhatsApp phone without 00
    label_stats   = t(lang,'q_stats');   wa1=f"https://wa.me/{phone}?text={quote(label_stats+' — '+title)}"
    label_method  = t(lang,'q_method');  wa2=f"https://wa.me/{phone}?text={quote(label_method+' — '+title)}"
    label_service = t(lang,'q_service'); wa3=f"https://wa.me/{phone}?text={quote(label_service+' — '+title)}"
    label_whats   = t(lang,'q_whatsapp');wa4=f"https://wa.me/{phone}?text={quote(title)}"
    parts=[]
    if pdf: parts.append(f'<a href="{pdf}" target="_blank">{t(lang,"dl_pdf")}</a>')
    if source: parts.append(f'<a href="{source}" target="_blank">{t(lang,"dl_src")}</a>')
    parts += [f'<a href="{wa1}" target="_blank">{label_stats}</a>',
              f'<a href="{wa2}" target="_blank">{label_method}</a>',
              f'<a href="{wa3}" target="_blank">{label_service}</a>',
              f'<a href="{wa4}" target="_blank">{label_whats}</a>']
    return " | ".join(parts)

# ---------------- Fetch & render ----------------
def signature_tuple(**kwargs):
    return tuple((k, kwargs.get(k)) for k in sorted(kwargs.keys()))

params_for_sig = dict(
    q=q, exact_phrase=locals().get("exact_phrase",""), any_words=locals().get("any_words",""),
    author=locals().get("author",""), venue=locals().get("venue",""),
    result_lang=locals().get("result_lang",""), years=locals().get("years",(1990,2030)),
    open_access_only=locals().get("open_access_only",False), doc_type=locals().get("doc_type",[]),
    sort_opt=locals().get("sort_opt",t(st.session_state.ui_lang,'sort_rel')), title_only=locals().get("title_only",False),
    strict_local=locals().get("strict_local",True),
)

sig = signature_tuple(**params_for_sig)

def display_page(results):
    st.success(f"{t(st.session_state.ui_lang,'total_results')}: {st.session_state.total_count:,}")
    st.caption(f"{t(st.session_state.ui_lang,'shown_after')}: {len(results):,}")

    # Export Excel for current page
    if results:
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
        st.download_button(t(st.session_state.ui_lang,"download_excel"), data=buf.getvalue(),
                           file_name="search_results_page.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Render each result
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
            f"🏷️ {t(st.session_state.ui_lang,'meta_venue')}: **{venue}**",
            f"👤 {t(st.session_state.ui_lang,'meta_authors')}: **{authors}**",
            f"📅 {t(st.session_state.ui_lang,'meta_year')}: **{year}**",
            f"📈 {t(st.session_state.ui_lang,'meta_citations')}: **{cites}**",
        ])
        st.caption(meta)
        st.markdown(actions_row(st.session_state.ui_lang, title, pdf, source), unsafe_allow_html=True)

        # Citation display + export
        c1, c2 = st.columns([1,1])
        with c1:
            with st.expander(f"📝 {t(st.session_state.ui_lang,'cite_style')} — {cite_style}"):
                st.code(fmt_citation(w, cite_style))
        with c2:
            ris_data = ris_entry(w).encode("utf-8")
            bib_data = bibtex_entry(w, idx=idx).encode("utf-8")
            st.download_button("RIS", data=ris_data, file_name=f"ref_{idx}.ris", mime="application/x-research-info-systems", key=f"ris_{idx}")
            st.download_button("BibTeX", data=bib_data, file_name=f"ref_{idx}.bib", mime="text/x-bibtex", key=f"bib_{idx}")
        st.markdown("---")

# Run search or show message
if do_search and q.strip():
    st.session_state.last_signature = sig
    st.session_state.cursor = "*"
    params = _build_params(**{k:params_for_sig[k] for k in ["q","exact_phrase","any_words","author","venue","result_lang","years","open_access_only","doc_type","sort_opt","title_only"]})
    raw_results, nxt_cursor, total = fetch_up_to(params, st.session_state.cursor, target_count=500)
    # local filters
    raw_results = _apply_exclude(raw_results, locals().get("none_words",""))
    raw_results = _apply_require(raw_results, params_for_sig["q"], params_for_sig["exact_phrase"], params_for_sig["any_words"], enabled=params_for_sig["strict_local"])
    st.session_state.page_results = raw_results
    st.session_state.cursor = nxt_cursor
    st.session_state.total_count = total
elif st.session_state.last_signature == sig and st.session_state.page_results:
    pass
else:
    st.info(t(st.session_state.ui_lang,'enter_keyword'))

# Render page results + paging
if st.session_state.page_results:
    display_page(st.session_state.page_results)
    if st.session_state.cursor:
        if st.button(t(st.session_state.ui_lang,"next_page")):
            params = _build_params(**{k:params_for_sig[k] for k in ["q","exact_phrase","any_words","author","venue","result_lang","years","open_access_only","doc_type","sort_opt","title_only"]})
            raw_results, nxt_cursor, total = fetch_up_to(params, st.session_state.cursor, target_count=500)
            raw_results = _apply_exclude(raw_results, locals().get("none_words",""))
            raw_results = _apply_require(raw_results, params_for_sig["q"], params_for_sig["exact_phrase"], params_for_sig["any_words"], enabled=params_for_sig["strict_local"])
            st.session_state.page_results = raw_results
            st.session_state.cursor = nxt_cursor
            st.session_state.total_count = total
            (getattr(st, "rerun", None) or st.experimental_rerun)()
    else:
        st.caption(t(st.session_state.ui_lang,"no_more_pages"))
