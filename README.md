# CloudSense AI

[![Platform Status](https://img.shields.io/badge/status-production--ready-emerald.svg)](#)
[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](#)
[![Next.js Version](https://img.shields.io/badge/next.js-15.4-black.svg)](#)
[![Tests Passing](https://img.shields.io/badge/tests-104%2F104%20passing-brightgreen.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](#)

> **See Your Cloud. Understand Your Spend. Decarbonize Intelligently.**
> CloudSense AI is an enterprise-grade multi-cloud FinOps, machine learning cost forecasting, automated resource remediation, and CarbonSense™ environmental intelligence platform across AWS, Azure, and Google Cloud Platform (GCP).

---

## 1. Architectural Overview

CloudSense AI bridges the gap between financial cost governance and carbon sustainability through a single authoritative source of truth. Every card, chart, report, and simulation reconciles with the database layer.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                  CloudSense AI Platform                                  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
        │                                  │                                  │
 ┌──────────────┐                  ┌──────────────┐                   ┌──────────────┐
 │ AWS Adapter  │                  │Azure Adapter │                   │ GCP Adapter  │
 │ IAM Role ARN │                  │Service Princ.│                   │Service Acct. │
 └──────────────┘                  └──────────────┘                   └──────────────┘
        │                                  │                                  │
        └──────────────────────────────────┼──────────────────────────────────┘
                                           ▼
                    ┌─────────────────────────────────────────┐
                    │ Multi-Tenant Normalization & Ingestion  │
                    │  Idempotent SHA-256 Deduplication Pipeline│
                    └─────────────────────────────────────────┘
                                           │
                                           ▼
                    ┌─────────────────────────────────────────┐
                    │ PostgreSQL 17 / SQLite 3 Local Database │
                    │   21 Normalized Enterprise Tables       │
                    └─────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
     ┌─────────────────────────────┐               ┌─────────────────────────────┐
     │  FinOps Intelligence Core   │               │   CarbonSense™ Engine       │
     │ • Polynomial Forecasting    │               │ • GHG Scope 1, 2, 3 Protocol│
     │ • Isolation Forest Anomaly  │               │ • EPA eGRID 2024 / EEA 2023 │
     │ • RCA Root Cause Engine     │               │ • Regional Grid Factors     │
     │ • Priority Scoring Engine   │               │ • Hardware Wattage Deltas   │
     └─────────────────────────────┘               └─────────────────────────────┘
                    │                                             │
                    └──────────────────────┬──────────────────────┘
                                           ▼
                    ┌─────────────────────────────────────────┐
                    │  FastAPI 0.116.1 Backend API Engine     │
                    │ • Enterprise RBAC (ADMIN, FINOPS, etc.) │
                    │ • Prometheus /metrics Plaintext Exporter│
                    │ • HMAC-SHA256 Signed Outbound Webhooks  │
                    │ • Shift-Left Terraform Plan Diff Engine │
                    │ • Kubernetes Container Allocation (Idle)│
                    └─────────────────────────────────────────┘
                                           │
                                           ▼
                    ┌─────────────────────────────────────────┐
                    │  Next.js 15 + React 19 Frontend Console │
                    │ • 25 Statically Generated Fast Routes   │
                    │ • Glassmorphism Design System           │
                    │ • Live Telemetry & What-If Simulators   │
                    └─────────────────────────────────────────┘
```

---

## 2. Complete 13-Phase Delivered Capabilities

| Phase | Subsystem | Key Capabilities & Invariants |
|---|---|---|
| **Phase 1** | **Audit & Data Stabilization** | Documented database baselines, eliminated zero-value chart regressions, isolated demo telemetry, and enforced non-fabrication invariants. |
| **Phase 2** | **Billing Import Engine** | Transactional CSV ingestion (`backend/app/services/billing_import.py`) with SHA-256 duplicate rejection, idempotency key replay, and zero partial writes. |
| **Phase 3** | **Cost Explorer & Data Lineage** | Multi-dimensional aggregation service (`/api/costs`), period-over-period tracking, and CSV export with formula-injection sanitization (`=`, `+`, `-`, `@`). |
| **Phase 4** | **Budgets, Alerts & Tag Governance** | Persistent budgets (`/api/budgets`), SHA-256 fingerprint deduplicated alerting, and compliance auditing across mandatory cost tags (`Environment`, `Owner`, `Project`). |
| **Phase 5** | **Forecasting, Anomalies & RCA** | Multi-horizon trend regression (7D–90D), dynamic confidence intervals (80%/95%), Isolation Forest anomaly detection, and deterministic Root Cause Analysis. |
| **Phase 6** | **CarbonSense™ Sustainability** | Source-aware greenhouse gas accounting (Scope 1, Scope 2 market/location, Scope 3) using published EPA eGRID 2024 and EEA 2023 regional grid intensity factors. |
| **Phase 7** | **Optimization, Simulator & Ledger** | Telemetry-grounded recommendations, 4 priority scoring modes (`BALANCE`, `COST`, `EMISSIONS`, `RISK_AVOIDANT`), read-only what-if simulator, and verified savings ledger. |
| **Phase 8** | **AI Analyst & Executive Reports** | Grounded AI assistant querying authorized backend tools, and database-reconciled PDF and sanitized CSV executive digest generation. |
| **Phase 9** | **Security, Identity & Collaboration** | FinOps RBAC (`ADMIN`, `FINOPS_ENGINEER`, `AUDITOR`, `VIEWER`), JWT JTI token revocation on logout (`RevokedToken`), and queryable structured audit trail (`/api/audit/logs`). |
| **Phase 10** | **Multi-Cloud Ingestion Connectors** | Pluggable read-only adapters (`backend/app/providers/`) for AWS, Azure, and GCP. Validates IAM Role ARNs and Service Principals with zero raw secret exposure. |
| **Phase 11** | **Background Jobs & Observability** | Task runner for periodic sweeps, `/health` active DB latency pings, Prometheus `/metrics` exporter, HMAC-SHA256 cryptographic webhooks, and human-in-the-loop remediation. |
| **Phase 12** | **Shift-Left IaC & Container FinOps** | Pre-deployment Terraform plan JSON cost & carbon diff analyzer, CI/CD policy guardrails (`PASSED`, `WARNING`, `BLOCKED`), and Kubernetes idle waste allocation (`/iac`). |
| **Phase 13** | **Release Readiness & Hardening** | Python 3.11 container hardening, automated secret scan across repository, deterministic master seed generator, and 100% test verification (104/104 tests). |

---

## 3. Technology Stack

- **Frontend**: Next.js 15.4.6 (App Router), React 19.1.1, TypeScript 5.8, Tailwind CSS 4, Recharts 2.15, Framer Motion 12.4.
- **Backend**: Python 3.11, FastAPI 0.116.1, Pydantic 2.11, SQLAlchemy 2.0, Passlib (bcrypt 4.3), ReportLab 4.4.
- **Analytics & ML**: Scikit-learn 1.7.1 (Isolation Forest), NumPy 2.3.2, Pandas 2.3.2.
- **Databases & Cache**: PostgreSQL 17 (production), SQLite 3 (local zero-dependency fallback), Redis 7 (caching/broker).
- **Testing**: Pytest 8.4.1 (104 tests across 14 specialized suites).

---

## 4. Quickstart Guide

### Option A: Running with Docker Compose (Recommended for Production/Evaluation)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

```bash
# 1. Clone repository
git clone https://github.com/your-org/cloudsense-ai.git
cd cloudsense-ai

# 2. Launch multi-container environment (PostgreSQL 17 + Redis 7 + Backend + Frontend)
docker compose up --build
```
- Frontend application: `http://localhost:3000`
- Interactive OpenAPI / Swagger documentation: `http://localhost:8000/docs`
- Prometheus Metrics Exporter: `http://localhost:8000/metrics`
- Subsystem Health Check: `http://localhost:8000/health`

---

### Option B: Local Development Setup (Zero-Docker SQLite Mode)

#### 1. Backend Service
```bash
# In the repository root:
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Seed demonstration database (NovaTech Solutions with 120 resources & 90-day telemetry)
bash scripts/seed.sh

# Start FastAPI development server
uvicorn backend.app.main:app --reload --port 8000
```

#### 2. Frontend Application
```bash
# In a new terminal tab:
cd frontend
npm install
npm run dev
```
Visit `http://localhost:3000` in your browser.

---

## 5. Demonstration Credentials

The deterministic seed script configures a multi-tenant demonstration organization (`NovaTech Solutions`):

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Platform Administrator** | `admin@cloudsense.ai` | `CloudSense@123` | Full administrative control, connectors, jobs, approvals |
| **FinOps Engineer** | *Created via `/settings`* | *Custom* | Connect accounts, trigger syncs, propose/approve actions |
| **Auditor** | *Created via `/settings`* | *Custom* | Read-only audit logs, executive digests, compliance |
| **Viewer** | *Created via `/settings`* | *Custom* | Read-only visibility across dashboards and analytics |

---

## 6. Frontend Navigation & Feature Map

```
/dashboard         Executive Overview: KPI Cards, Cost Trend, Provider Breakdown, Anomaly Alerts
/cloud-accounts    Multi-Cloud Connectors: AWS, Azure, GCP Credentials, Sync Jobs, Status
/costs             Authoritative Cost Explorer: Group by Service/Provider, Date Filters, Sanitized CSV Export
/forecast          Multi-Horizon ML Forecast: 7D-90D Horizons, 80%/95% Confidence Bounds, MAE/RMSE
/anomalies         Anomaly Detection Center: Isolation Forest Residual Envelopes & Impact Analysis
/rca               Root Cause Analysis: Deterministic Diagnostics & Explanations
/optimization      Optimization & Simulator: Priority Modes, What-If Scenarios, Savings Ledger
/iac               Shift-Left IaC & Container FinOps: Terraform Plan Diff, Policies, K8s Idle Waste
/carbon            CarbonSense™ Engine: GHG Scope 1/2/3 Breakdown, EPA eGRID Factors, Emissions Budgets
/security          Cloud Security & Compliance Findings
/sla               Multi-Cloud Service Level Agreement (SLA) & Uptime Tracking
/budgets           Persistent Budgets: Live Spend Aggregations, Threshold Alerts, Burn-Rates
/alerts            Deduplicated Alert Inbox: Triage Workflows (New, In Progress, Resolved)
/assistant         Grounded AI FinOps Analyst: Natural Language Answers from Database Tools
/system            System & Ops: Telemetry Diagnostics, Background Jobs Queue, Action Remediation, Webhooks
/reports           Executive PDF & CSV Digest Generator
/settings          Workspace Profile, User Management, RBAC Roles, and Queryable Audit Logs
```

---

## 7. Automated Test Suite & Verification

CloudSense AI enforces rigorous automated testing across every subsystem:

```bash
# Run complete test suite (104 tests across 14 suites)
.venv/bin/pytest -v
```

### Test Suite Inventory:
1. `backend/tests/test_iac_container_finops.py`: Terraform plan parsing, cost & carbon diffs, CI/CD policy gates, Kubernetes idle waste.
2. `backend/tests/test_background_jobs_observability.py`: Health diagnostics, Prometheus metrics, background task runner, HMAC-SHA256 webhooks, remediation actions.
3. `backend/tests/test_multicloud_connectors.py`: AWS IAM Role ARNs, Azure Service Principals, GCP Service Accounts, duplicate rejection, idempotent sync.
4. `backend/tests/test_security_identity_collaboration.py`: RBAC role barriers, JTI session revocation, audit logging, multi-tenant isolation.
5. `backend/tests/test_ai_analyst_reporting.py`: Reconciled PDF generation, formula injection protection, background report jobs.
6. `backend/tests/test_optimization_simulator.py`: Hardware wattage carbon math, priority scoring, read-only what-if simulator, savings ledger.
7. `backend/tests/test_forecast_anomalies.py`: Multi-horizon forecasts, evaluation metrics, anomaly envelopes, root cause analysis.
8. `backend/tests/test_carbonsense.py`: Carbon summary aggregation, GHG Scope classification, EPA factors, CSV import, carbon budgets.
9. `backend/tests/test_cost_explorer.py`: Reconciliation invariants, data lineage, formula injection sanitization, multi-tenant costs.
10. `backend/tests/test_budgets_alerts.py`: Budget CRUD, threshold transitions, fingerprint deduplicated alerts, tag compliance.
11. `backend/tests/test_billing_import.py`: Transactional CSV ingestion, duplicate rejection, idempotency replay, zero partial writes.
12. `backend/tests/test_dashboard.py`: Subsystem health, demo login, dashboard metrics, empty organization regressions.
13. `backend/tests/test_auth.py`: Password hashing and token security.
14. `backend/tests/test_ml.py`: Regression trend forecasts and Isolation Forest anomaly baselines.

```bash
# Verify frontend production build (25 routes)
cd frontend
npm run build
```

---

## 8. Security & Non-Fabrication Invariants

1. **Non-Fabrication Policy**: In the absence of live cloud provider credentials, connections activate *"CONNECTED (Simulated / Non-Fabricated Telemetry Mode)"* and explicitly flag `is_simulated: true`. No false socket claims or phantom billing calls are made.
2. **Zero Raw Secret Exposure**: Sensitive credentials in `cloud_accounts` (`credentials_masked`) redact private keys and secret tokens (`****************`). Outbound webhook secrets are stored securely for signature validation.
3. **Cryptographic Signatures**: Outgoing webhooks are authenticated with HMAC-SHA256 signatures in `X-CloudSense-Signature: sha256=...`.
4. **Human-in-the-Loop Safeguards**: Remediation actions strictly default to `PROPOSED`; state mutating execution mandates approval by `ADMIN` or `FINOPS_ENGINEER`. Every action mandates an automated or documented `rollback_plan`.
5. **CSV Formula Injection Sanitization**: All tabular and report CSV export cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are sanitized with single-quote escaping to prevent execution in spreadsheet software.
6. **Strict Multi-Tenancy**: Every query and write operation partitions by authenticated `organization_id`. Cross-tenant queries return 404 Not Found.

---

## 9. License

This project is licensed under the MIT License — see the LICENSE file for details.
