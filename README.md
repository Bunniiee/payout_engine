# Payout Engine

A production-grade payout engine for merchants receiving international payments. Merchants accumulate INR balance from customer payments and withdraw to their Indian bank accounts. The engine handles concurrent payout requests, idempotency, strict state machine transitions, and background processing with automatic retry logic.

**Live Dashboard**: https://payout-engine-weld.vercel.app

---

## Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL (amounts stored as BigIntegerField in paise — no floats)
- **Queue**: Celery 5.3 + Redis
- **Frontend**: React 18 + Vite + Tailwind CSS
- **Deployment**: Railway (backend + celery worker + beat scheduler) + Vercel (frontend)

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15
- Redis 7

### 1. Clone and create environment

```bash
git clone https://github.com/Bunniiee/payout_engine.git
cd payout_engine
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
5. Set the **Start Command** to `bash start.sh` — this runs collectstatic, migrate, seed, celery+beat, and gunicorn
6. Set the **Port** in Railway networking settings to match the `PORT` env var (default 8080)

## Vercel Deployment (Frontend)

1. Connect the GitHub repository to Vercel
2. Set **Root Directory** to `frontend`
3. Add environment variable: `VITE_API_URL=https://<your-railway-domain>.up.railway.app`
4. Deploy

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
