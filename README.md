# Baking E-commerce Backend

FastAPI + MongoDB backend for a baking e-commerce website (Theobroma-style).
Supports customers and admins, with product management, cart, and orders.

## Tech Stack
- FastAPI
- MongoDB (Motor async driver)
- JWT Authentication
- Local filesystem for images

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then fill in your values
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/` for the health check, and
`http://127.0.0.1:8000/docs` for interactive API docs.

## Project Structure
```
app/
├── main.py            # FastAPI app entry point
├── core/               # config, security
├── models/             # Pydantic + DB models
├── schemas/             # request/response validation
├── api/v1/              # route handlers (routers)
└── database/            # DB connection
```
