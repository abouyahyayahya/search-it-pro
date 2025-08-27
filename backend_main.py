# backend_main.py
# FastAPI microservice: /v1/search (free-then-email with mailto rotation),
# /v1/search_bulk (up to 2000 via cursor), OA Link Resolver, Bank-only flow, Owner override (trusted device)
import os, re, time, hmac, hashlib, base64, requests
from typing import Optional, Dict, List
from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File, Form, Response, Query
from fastapi.middleware.cors import CORSMiddleware

APP = FastAPI(title="SearchItPro Backend")
APP.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

UA = "SearchItPro/1.0"
OPENALEX_BASE = "https://api.openalex.org/works"
TIMEOUT = 30

# --------- OWNER MAILTOS (rotation for first-free only) ----------
OWNER_MAILTOS = [e.strip() for e in os.getenv(
    "OWNER_MAILTOS",
    "doctormahmoud1984@gmail.com,yah20252025@gmail.com,drmahmoud@azhar.edu.eg"
).split(",") if e.strip()]

# --------- Bank ENV (kept secret; we only reveal masked) ----------
BANK = {
    "iban": os.getenv("BANK_IBAN",""),
    "bic": os.getenv("BANK_BIC",""),
    "name": os.getenv("BANK_NAME",""),
    "branch": os.getenv("BANK_BRANCH",""),
    "currency": os.getenv("BANK_CURRENCY","USD"),
    "benef_first": os.getenv("BANK_BENEFICIARY_FIRST_NAME","Mahmoud"),
    "benef_last":  os.getenv("BANK_BENEFICIARY_LAST_NAME","Hassaneen"),
    "country": os.getenv("BANK_COUNTRY","EG"),
    "city": os.getenv("BANK_CITY","Kafr Aldawar"),
    "state": os.getenv("BANK_STATE","Behera"),
    "street": os.getenv("BANK_STREET","Masjid Ebad Al Rahman"),
    "street_no": os.getenv("BANK_STREET_NO","222"),
    "postal": os.getenv("BANK_POSTAL_CODE","22625"),
    "phone": os.getenv("BANK_PHONE_E164","+201020161059"),
}
def mask(v: str, keep=4) -> str:
    if not v: return ""
    s = v.replace("+","")
    return s[:2] + "•"*(max(0,len(s)-2-keep)) + s[-keep:]

def valid_iban_eg(iban: str) -> bool:
    if not iban: return False
    s = re.sub(r"\s+", "", iban).upper()
    if len(s) != 29: return False  # Egypt IBAN length
    s2 = s[4:] + s[:4]
    nums = ""
    for ch in s2:
        if ch.isdigit(): nums += ch
        elif "A" <= ch <= "Z": nums += str(ord(ch)-55)
        else: return False
    r = 0
    for c in nums:
        r = (r*10 + int(c)) % 97
    return r == 1

# --------- OTP + Signed cookies (light) ----------
SECRET = os.getenv("BACKEND_SECRET","change-me")
def sign_token(payload: str) -> str:
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")

OTP_STORE: Dict[str, Dict] = {}  # email -> {"code":..., "exp":...}

# --------- First-free tracking ----------
FREE_TTL_SEC = 24*3600
FREE_USED: Dict[str, float] = {}  # ip -> last ts

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
def looks_like_email(x: str) -> bool: return bool(x and EMAIL_RE.match(x))

def ip_from_request(req: Request) -> str:
    fwd = req.headers.get("x-forwarded-for") or ""
    if fwd: return fwd.split(",")[0].strip()
    return req.client.host if req.client else "0.0.0.0"

def free_allowed(ip: str) -> bool:
    t = FREE_USED.get(ip)
    now = time.time()
    return (not t) or ((now - t) > FREE_TTL_SEC)

def mark_free_used(ip: str): FREE_USED[ip] = time.time()

def pick_owner_mailto(ip: str) -> str:
    if not OWNER_MAILTOS: return ""
    h = int(hashlib.sha256(ip.encode()).hexdigest(), 16)
    return OWNER_MAILTOS[h % len(OWNER_MAILTOS)]

# --------- OA Link Resolver (Unpaywall + Semantic Scholar) ----------
UNPAYWALL_MAILTO = os.getenv("UNPAYWALL_MAILTO","")

def try_unpaywall(doi: str) -> Dict:
    if not doi: return {}
    url = f"https://api.unpaywall.org/v2/{doi}"
    params = {"email": UNPAYWALL_MAILTO} if UNPAYWALL_MAILTO else {}
    r = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": UA})
    if r.ok:
        j = r.json()
        best = j.get("best_oa_location") or {}
        return {
            "oa_pdf_url": best.get("url_for_pdf") or "",
            "oa_html_url": best.get("url") or "",
            "provenance": "Unpaywall"
        }
    return {}

def try_semanticscholar(doi: str) -> Dict:
    if not doi: return {}
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    r = requests.get(url, params={"fields":"title,openAccessPdf,url"}, timeout=TIMEOUT, headers={"User-Agent": UA})
    if r.ok:
        j = r.json()
        pdf = (j.get("openAccessPdf") or {}).get("url") or ""
        if pdf: return {"oa_pdf_url": pdf, "provenance":"SemanticScholar"}
    return {}

@APP.get("/health")
def health(): return {"ok": True}

@APP.get("/resolve")
def resolve_oa(doi: Optional[str] = None, title: Optional[str] = None):
    out = {"oa_pdf_url":"", "oa_html_url":"", "publisher_landing_url":"", "provenance":""}
    if doi:
        u = try_unpaywall(doi)
        if u.get("oa_pdf_url") or u.get("oa_html_url"): out.update(u)
        if not out["oa_pdf_url"]:
            s = try_semanticscholar(doi)
            if s.get("oa_pdf_url"): out.update(s)
        out["publisher_landing_url"] = f"https://doi.org/{doi}"
    return out

# --------- Search: first-free, then require email (mailto) ----------
@APP.get("/v1/search")
def search(
    q: str = Query(..., min_length=1),
    per_page: int = Query(25, ge=1, le=200),
    user_mailto: str | None = None,
    request: Request = None,
    x_api_key: str = Header(None),
):
    ip = ip_from_request(request)
    params = {"search": q, "per_page": per_page}
    selected_mailto = ""

    if user_mailto and looks_like_email(user_mailto):
        selected_mailto = user_mailto.strip()
    else:
        if free_allowed(ip):
            selected_mailto = pick_owner_mailto(ip)
            mark_free_used(ip)
        else:
            raise HTTPException(
                status_code=428,
                detail={
                    "message": "Email required after the first successful search.",
                    "why": "We use your email only as a 'mailto' to OpenAlex for a stable, fair quota.",
                    "docs": "https://docs.openalex.org/how-to-use-the-api/rate-limits-and-mailto",
                    "hint_ar": "بعد أول نتيجة ناجحة يجب إدخال بريدك، ويُستخدم فقط كـ mailto لتحسين حصتك."
                }
            )

    if selected_mailto: params["mailto"] = selected_mailto
    headers = {"User-Agent": f"{UA} ({'mailto:'+selected_mailto if selected_mailto else 'no-mailto'})"}
    r = requests.get(OPENALEX_BASE, params=params, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return {"mailto_used": selected_mailto, "count": data.get("meta", {}).get("count", 0), "results": data.get("results", [])}

# --------- Bulk search up to 2000 (cursor pagination) ----------
@APP.get("/v1/search_bulk")
def search_bulk(
    q: str = Query(..., min_length=1),
    target_count: int = Query(2000, ge=1, le=2000),
    request: Request = None,
    user_mailto: str | None = None,
):
    ip = ip_from_request(request)
    params = {"search": q, "per_page": 200, "cursor": "*"}
    selected_mailto = ""
    if user_mailto and looks_like_email(user_mailto):
        selected_mailto = user_mailto.strip()
    else:
        if free_allowed(ip):
            selected_mailto = pick_owner_mailto(ip)
            mark_free_used(ip)
        else:
            raise HTTPException(428, "Email required after first success.")
    if selected_mailto: params["mailto"] = selected_mailto

    headers = {"User-Agent": f"{UA} ({'mailto:'+selected_mailto if selected_mailto else 'no-mailto'})"}
    out: List[Dict] = []
    hops = 0
    while len(out) < target_count and hops < 20:
        r = requests.get(OPENALEX_BASE, params=params, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        j = r.json()
        out.extend(j.get("results", []))
        nxt = (j.get("meta") or {}).get("next_cursor")
        if not nxt: break
        params["cursor"] = nxt
        hops += 1

    return {"mailto_used": selected_mailto, "results": out[:target_count]}

# --------- Bank flow (OTP -> masked reveal -> upload proof) ----------
@APP.post("/bank/reveal")
def bank_reveal(email: str = Form(...), otp: Optional[str] = Form(None), response: Response = None):
    now = time.time()
    if not otp:
        code = str(int(now) % 1000000).zfill(6)
        OTP_STORE[email] = {"code": code, "exp": now + 600}
        return {"status":"OTP_SENT","hint":"Check your email for a 6-digit code."}
    rec = OTP_STORE.get(email)
    if not rec or now > rec["exp"] or otp != rec["code"]: raise HTTPException(400, "Invalid or expired OTP")
    if not valid_iban_eg(BANK["iban"]): raise HTTPException(500, "Bank IBAN misconfigured")
    payload = f"{email}:{int(now)}"
    token = sign_token(payload)
    response.set_cookie("bank_session", token, max_age=600, httponly=True, samesite="lax")
    return {
        "status":"OK",
        "iban_masked": mask(BANK["iban"], keep=4),
        "bic": BANK["bic"],
        "bank": BANK["name"], "branch": BANK["branch"], "currency": BANK["currency"],
        "beneficiary": f"{BANK['benef_first']} {BANK['benef_last']}",
        "address": f"{BANK['street_no']}, {BANK['street']}, {BANK['city']}, {BANK['state']}, {BANK['postal']}, {BANK['country']}",
        "phone_masked": mask(BANK["phone"], keep=4),
    }

@APP.post("/bank/proof")
async def bank_proof(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 8_000_000: raise HTTPException(400, "File too large")
    return {"status":"RECEIVED","filename": file.filename, "size": len(content)}

# --------- Tickets: Assist (20$) & Services (50$/120$) ----------
@APP.post("/assist/init")
def assist_init(work_id: str = Form(...), title: str = Form(""), email: str = Form(""), questions: str = Form("")):
    return {"status":"CREATED", "assist_id": int(time.time()), "deposit_usd": 20}

@APP.post("/svc/init")
def svc_init(svc_type: str = Form(...), name: str = Form(""), email: str = Form(""), whatsapp: str = Form(""),
             due: str = Form(""), notes: str = Form(""), entries: str = Form(""), files_count: int = Form(0)):
    amount = 120 if svc_type == "summarize_prior_studies" else 50
    return {"status":"CREATED", "service_id": int(time.time()), "deposit_usd": amount}

# --------- Owner override (trusted device) ----------
OWNER_EMAILS = set(e.strip().lower() for e in [
    "doctormahmoud1984@gmail.com",
    "yah20252025@gmail.com",
    "drmahmoud@azhar.edu.eg",
] if e)

@APP.post("/owner/init")
def owner_init(email: str = Form(...)):
    e = email.strip().lower()
    if e not in OWNER_EMAILS: raise HTTPException(403, "Not allowed")
    code = str(int(time.time()) % 1000000).zfill(6)
    OTP_STORE["owner:"+e] = {"code": code, "exp": time.time() + 600}
    return {"status":"OTP_SENT"}

@APP.post("/owner/verify")
def owner_verify(email: str = Form(...), otp: str = Form(...), response: Response = None):
    rec = OTP_STORE.get("owner:"+email.strip().lower())
    if not rec or time.time()>rec["exp"] or otp != rec["code"]:
        raise HTTPException(400, "Invalid or expired OTP")
    payload = f"owner:{email}:{int(time.time())}"
    token = sign_token(payload)
    response.set_cookie("owner_override", token, max_age=180*24*3600, httponly=True, samesite="lax")
    return {"status":"OK", "owner_token": token}
