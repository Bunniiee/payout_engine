# Playto Payout Engine

A production-grade payout engine for Indian merchants receiving international payments. Merchants accumulate INR balance and withdraw to their bank accounts. Built as a Founding Engineer technical assessment for Playto Pay.

**Live URL**: _to be filled after Railway deployment_

---

## Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 15 (amounts stored as BigIntegerField in paise — no floats)
- **Queue**: Celery 5.3 + Redis 7
- **Frontend**: React 18 + Vite + Tailwind CSS
- **Deployment**: Railway (web + worker + beat via Procfile)

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15
- Redis 7

### 1. Clone and create environment

```bash
git clone <repo-url>
cd payment_infra
cp .env.example .env
# Edit .env with your DB and Redis credentials
```

### 2. Create the database

```bash
psql -U postgres -c "CREATE USER playto WITH PASSWORD 'playto';"
psql -U postgres -c "CREATE DATABASE playto OWNER playto;"
```

### 3. Install backend dependencies

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Run migrations and seed data

```bash
python manage.py migrate
python manage.py seed_db
```

### 5. Start backend services

```bash
# Terminal 1 — Django dev server
python manage.py runserver

# Terminal 2 — Celery worker
celery -A playto worker --loglevel=info

# Terminal 3 — Celery beat (retry scheduler)
celery -A playto beat --loglevel=info
```

### 6. Start frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## Docker (alternative)

```bash
cp .env.example .env
docker-compose up --build
```

Runs all 5 services: postgres, redis, web, worker, beat.

---

## Running Tests

```bash
python manage.py test tests --verbosity=2
```

Two tests:
- `test_concurrency.py` — two simultaneous 60-rupee payouts on 100-rupee balance; exactly one succeeds
- `test_idempotency.py` — same idempotency key twice; same payout returned, balance debited once

---

## Railway Deployment

1. Create a new Railway project
2. Add **PostgreSQL** plugin and **Redis** plugin
3. Connect your GitHub repository
4. Set environment variables in Railway dashboard (see `.env.example`)
5. Railway uses the `Procfile` automatically:
   ```
   web:    gunicorn playto.wsgi --bind 0.0.0.0:$PORT --workers 2
   worker: celery -A playto worker --loglevel=info --concurrency=2
   beat:   celery -A playto beat --loglevel=info
   ```
6. After first deploy, run seed:
   ```bash
   railway run python manage.py seed_db
   ```
7. Build and deploy the `frontend/` as a static site (or serve via a separate Railway service)

---

## API

All endpoints require `X-Merchant-ID: <uuid>` header.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/merchants/` | List all merchants |
| GET | `/api/v1/merchants/me/` | Current merchant balance |
| POST | `/api/v1/payouts/` | Create payout (requires `Idempotency-Key` header) |
| GET | `/api/v1/payouts/` | List payouts |
| GET | `/api/v1/payouts/<id>/` | Payout detail |
| GET | `/api/v1/ledger/` | Ledger entries |
