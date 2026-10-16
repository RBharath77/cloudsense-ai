# Academic Documentation Map
Problem Statement: fragmented multi-cloud spend and operations make cost, reliability, security and sustainability decisions difficult.

Existing System: separate provider consoles and isolated cost/monitoring tools.

Proposed System: CloudSense AI unifies provider data through normalization, analytics, ML forecasting/anomaly detection, optimization, security, SLA, carbon and an application-data assistant.

Use Case Diagram actors: Admin, Manager, Developer, Viewer. Core use cases: authenticate, connect cloud, inspect spend/resources, analyze anomalies, review optimization, inspect security/SLA/carbon, manage budgets/alerts, generate report, query assistant.

DFD Level 0: User ↔ CloudSense AI ↔ Cloud Providers/Notification Services.
DFD Level 1: ingestion → normalization → PostgreSQL → analytics/ML → API → UI/assistant/reports/alerts.

ER Diagram entities correspond to `backend/app/models/__init__.py` and include foreign-key identifiers for organization, accounts, resources, metrics, recommendations, alerts, reports and audit events.
