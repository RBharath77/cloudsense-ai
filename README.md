# CloudSense AI

**See Your Cloud. Understand Your Spend. Optimize Intelligently.**

CloudSense AI is a production-style academic/portfolio foundation for multi-cloud cost intelligence across AWS, Azure and GCP. It follows the requested provider → normalization → database → ML → AI → FastAPI → Next.js flow and runs without cloud credentials in `CLOUD_MODE=mock`. fileciteturn0file0L114-L157

## Implemented in this first working build
- Next.js + TypeScript frontend with responsive SaaS shell
- FastAPI + Pydantic + SQLAlchemy backend
- JWT authentication and role field
- Seeded NovaTech Solutions demo organization and three provider accounts
- 120 cloud resources, 90-day metric/cost history, anomalies, recommendations, security, SLA, carbon, budget and alerts
- Provider abstraction with mock/AWS/Azure/GCP class boundaries
- Forecasting using a real regression model with MAE/RMSE
- Anomaly module using Isolation Forest
- Optimization recommendations based on utilization/cost
- RCA endpoint and UI
- Predictive scaling endpoint/UI
- Assistant grounded in application database data with deterministic fallback
- PDF executive report generation
- Safe recommendation simulation; no real cloud mutation
- Docker Compose for PostgreSQL + Redis + backend + frontend
- Pytest unit tests and documentation skeleton

## Local development (without Docker)
### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000
```
The local fallback database is SQLite when `DATABASE_URL` is not set. For PostgreSQL, export the PostgreSQL URL from `.env.example`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` and API docs at `http://localhost:8000/docs`.

### Demo login
`admin@cloudsense.ai` / `CloudSense@123` — DEVELOPMENT/DEMO ONLY.

## Docker
On a machine with Docker:
```bash
docker compose up --build
```

## Notes
The mock engine is deterministic and intentionally connected: resources have utilization/cost/metrics, and derived analytics operate on the same database. Demo numbers are not measurements of real cloud accounts. Carbon is explicitly estimated. Real cloud providers are architectural adapters and must be configured server-side before production use.
