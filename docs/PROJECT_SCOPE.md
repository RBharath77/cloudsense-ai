# CloudSense AI — Complete Product Scope and Technical Blueprint

**Product name:** CloudSense AI  
**Positioning:** Intelligent Cloud Cost, Optimization & Carbon Intelligence Platform  
**Primary priority:** Upgrade the existing repository; do not rebuild it blindly.  
**Status rule:** Every feature listed here is planned until it has been inspected, implemented, and tested against its acceptance criteria.

## 1. Product vision
CloudSense AI helps developers, startups, cloud engineers, project owners, finance teams, and small businesses understand cloud expenditure, forecast future bills, control budgets, investigate cost anomalies, identify supportable optimization opportunities, and understand the environmental impact of cloud usage.

The product's differentiator is a shared data and decision workflow that connects cloud financial management (FinOps) with carbon intelligence. It must not be a static dashboard or a set of disconnected demo pages.

## 2. Non-negotiable product principles
1. **Real source of truth:** The backend/database is authoritative. Frontend cards, charts, AI answers, and exports use shared service-layer aggregations.
2. **Evidence over appearance:** A feature is not complete because a screen or route exists.
3. **No fabricated metrics:** No fake production cost, emissions, utilization, accuracy, savings, integrations, job statuses, tests, or deployment claims.
4. **Transparent demonstration mode:** Demo records must be flagged and isolated from real records.
5. **Traceability:** Important metrics should expose period, filters, source, units, and, where useful, their underlying imports/records.
6. **Security by design:** Server-side authorization, organization/workspace isolation, least-privilege provider credentials, auditability, and secret protection.
7. **Explainable analytics:** Forecasts, anomaly flags, optimization advice, and carbon estimates state why they were produced and what assumptions apply.
8. **Preserve working code:** Inspect the live repo before altering architecture. Reuse and extend working modules.
9. **Incremental delivery:** Implement one phase and test it before moving on.

## 3. Users and roles
- Platform admin
- Workspace owner
- Team manager
- Analyst
- Viewer

## 4. Architecture and Stack
- **Frontend:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Recharts, Framer Motion.
- **Backend:** Python FastAPI, Pydantic, SQLAlchemy 2.0.
- **Database:** PostgreSQL (with SQLite for local development fallback).
- **ML / Analytics:** Scikit-learn (Isolation Forest for anomalies), NumPy/Pandas (Polynomial regression trend forecast with confidence intervals, MAE, RMSE).
- **Reporting:** ReportLab PDF generation.
- **Authentication:** JWT Bearer tokens with bcrypt password hashing and organization-level multi-tenancy.
