# SearchItPro — One-shot Upload Bundle
Generated: 2025-08-27T04:19:18.349676Z

## Files
- backend_main.py — FastAPI microservice (first-free search + mailto rotation; OA resolver; bank-only; services; owner override)
- app.py — Streamlit UI (email after first success; Help me; Services; 2000 results; Publish Articles)
- ui_helpers.py — helpers (GeoIP, flags, watermark, footer)
- requirements.txt — dependencies
- Articles_Word_Template.docx — basic article template (download from Publish Articles modal)
- .streamlit/secrets.example.toml — example secrets
- .gitignore

## Deploy (All from the browser)
1) **GitHub**: create a branch (feature/service-center-bank-only). Upload these files (Add file → Upload files) then open a Pull Request and merge to main.
2) **Render** (Backend):
   - New → Web Service → connect repo
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn backend_main:APP --host 0.0.0.0 --port $PORT`
   - ENV (do **NOT** commit secrets):
     OWNER_MAILTOS=doctormahmoud1984@gmail.com,yah20252025@gmail.com,drmahmoud@azhar.edu.eg
     BANK_* (as shared)
     UNPAYWALL_MAILTO=your-mail@example.com
     BACKEND_SECRET=change-me
   - Take service URL, e.g. https://searchitpro-backend.onrender.com

3) **Streamlit Cloud** (Frontend):
   - Main file: `app.py`
   - Secrets:
     BACKEND_URL = "https://searchitpro-backend.onrender.com"
     OWNER_FULLNAME_AR = "د. محمود أحمد الرفاعي حسانين أبو العلامين"
     OWNER_FULLNAME_EN = "Dr. Mahmoud Ahmed Alrefaey Hassaneen Abu Al Alamein"
     OWNER_PHOTO_URL = "https://example.com/your_photo.jpg"
     HIDE_PAID_FEATURES_IN_EG = "true"
     WATERMARK = "true"

## Sources
OpenAlex — rate limits & mailto: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-mailto
OpenAlex — works/open access: https://docs.openalex.org/api-entities/works/object-structure#open-access
OpenAlex — pagination: https://docs.openalex.org/how-to-use-the-api/api-overview#pagination
Unpaywall API: https://unpaywall.org/products/api
Semantic Scholar API: https://api.semanticscholar.org/api-docs/
