# FindAllEasy AI Engine v1 (Flask API)

Endpoints:
- GET /api/health
- GET /api/search?q=iPhone&region=TR&lang=tr
- GET /api/trends?region=TR
- GET /api/recommendations?user=guest&last=iPhone

Render deploy:
- Build Command: pip install -r requirements.txt
- Start Command: python app.py
- Env: ALLOWED_ORIGINS=https://www.findalleasy.com
