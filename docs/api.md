# CloudSense AI — API Reference

The interactive OpenAPI / Swagger specification is served at `/docs` (and ReDoc at `/redoc`). All authenticated endpoints mandate `Authorization: Bearer <JWT>` header.

---

## 1. Authentication & Session Security
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | Public | Register new organization and initial platform administrator. |
| `POST` | `/api/auth/login` | Public | Authenticate user credentials and return JWT bearer token. |
| `POST` | `/api/auth/logout` | Authenticated | Revoke JWT token JTI, adding it to the `revoked_tokens` blocklist. |
| `GET` | `/api/auth/me` | Authenticated | Return profile and role of authenticated user. |

---

## 2. Health & Observability
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/health` | Public | Healthcheck measuring active DB latency ping, disk status, and uptime. Returns `{"status": "ok", ...}`. |
| `GET` | `/health/detailed` | `ADMIN`, `AUDITOR` | Deep subsystem telemetry (database, disk, memory RSS, job execution rates). |
| `GET` | `/metrics` | Public | Prometheus-compatible plaintext metrics exporter. |
| `GET` | `/api/system/observability` | Authenticated | System dashboard telemetry, recent jobs, and pending action counts. |

---

## 3. Cost Governance & Aggregations
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/dashboard/summary` | Authenticated | Real-time KPI metrics, period spend, and provider cost distributions. |
| `GET` | `/api/costs` | Authenticated | Multi-dimensional cost records with provider, service, and date filtering. |
| `GET` | `/api/costs/daily` | Authenticated | Daily cost time series with grouping. |
| `GET` | `/api/costs/lineage` | Authenticated | Provenance data tracing costs back to ingestion imports. |
| `GET` | `/api/costs/export` | Authenticated | Streaming CSV export protected against spreadsheet formula injection. |
| `POST` | `/api/billing/import` | `ADMIN`, `FINOPS_ENGINEER` | Transactional CSV billing import with SHA-256 duplicate rejection. |

---

## 4. Machine Learning Forecasts, Anomalies & RCA
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/forecast` | Authenticated | Multi-horizon trend regression (7D–90D) with 80%/95% confidence bounds. |
| `GET` | `/api/anomalies` | Authenticated | Isolation Forest anomalies with financial impact and deviation score. |
| `POST` | `/api/anomalies/detect` | `ADMIN`, `FINOPS_ENGINEER` | Run dynamic anomaly sweep across recent telemetry. |
| `GET` | `/api/anomalies/{id}/rca` | Authenticated | Root Cause Analysis diagnostic breakdown. |

---

## 5. CarbonSense™ Sustainability Engine
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/carbon/summary` | Authenticated | GHG Protocol Scope 1, Scope 2 (market/location), Scope 3 totals. |
| `GET` | `/api/carbon/records` | Authenticated | Filtered carbon emission records. |
| `GET` | `/api/carbon/factors` | Authenticated | Published regional grid intensity factors (EPA eGRID 2024 / EEA 2023). |
| `POST` | `/api/carbon/import` | `ADMIN`, `FINOPS_ENGINEER` | Ingest normalized carbon emissions CSV. |
| `GET` | `/api/carbon/budgets` | Authenticated | List annual/monthly emissions caps and targets. |
| `POST` | `/api/carbon/budgets` | `ADMIN`, `FINOPS_ENGINEER` | Create new carbon emissions cap. |

---

## 6. Optimization, Simulator & Ledger
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/recommendations` | Authenticated | Telemetry-grounded recommendations with priority scoring modes. |
| `GET` | `/api/recommendations/{id}` | Authenticated | Line-item evidence, utilization percentiles, and trade-offs. |
| `POST` | `/api/simulator/run` | Authenticated | Read-only what-if simulator (fleet rightsizing, off-hours schedules, green grids). |
| `GET` | `/api/savings-ledger` | Authenticated | Verified savings ledger separating expected from measured realization. |
| `POST` | `/api/savings-ledger` | `ADMIN`, `FINOPS_ENGINEER` | Create manual savings verification ledger entry. |

---

## 7. Shift-Left IaC & Container FinOps
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/iac/terraform/analyze` | `ADMIN`, `FINOPS_ENGINEER` | Ingest Terraform plan JSON, compute cost/carbon deltas, evaluate CI/CD policies. |
| `GET` | `/api/iac/terraform/analyses` | Authenticated | List historical plan analyses and policy verdicts. |
| `GET` | `/api/iac/terraform/analyses/{id}` | Authenticated | Detailed plan breakdown with line-item resource changes. |
| `GET` | `/api/containers/kubernetes/allocations`| Authenticated | Workload allocations across namespaces measuring active vs idle spend. |
| `GET` | `/api/containers/kubernetes/summary` | Authenticated | Cluster summary (Total Cost, Active Spend, Idle Waste, Efficiency %). |
| `POST` | `/api/containers/kubernetes/ingest` | `ADMIN`, `FINOPS_ENGINEER` | Ingest container telemetry from Kubecost/Prometheus/cAdvisor. |

---

## 8. Multi-Cloud Ingestion Connectors
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/cloud/accounts` | Authenticated | List connected cloud accounts with sanitized credential masking. |
| `POST` | `/api/cloud/accounts` | `ADMIN`, `FINOPS_ENGINEER` | Connect AWS IAM Role ARN, Azure Service Principal, or GCP Service Account. |
| `POST` | `/api/cloud/accounts/{id}/sync` | `ADMIN`, `FINOPS_ENGINEER` | Trigger background ingestion job for connected account. |
| `GET` | `/api/cloud/accounts/{id}/jobs` | Authenticated | List synchronization job execution history. |
| `DELETE` | `/api/cloud/accounts/{id}` | `ADMIN` | Disconnect and remove a cloud account. |

---

## 9. Background Jobs, Webhooks & Automated Actions
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/jobs` | Authenticated | Query background execution queue and job states. |
| `POST` | `/api/jobs/trigger` | `ADMIN`, `FINOPS_ENGINEER` | Trigger on-demand task sweep (`ANOMALY_SWEEP`, `BUDGET_AUDIT`, etc.). |
| `DELETE` | `/api/jobs/{id}` | `ADMIN` | Cancel a queued or running background job. |
| `GET` | `/api/webhooks` | Authenticated | List registered outbound webhook endpoints. |
| `POST` | `/api/webhooks` | `ADMIN` | Register webhook destination with HMAC-SHA256 secret token generation. |
| `POST` | `/api/webhooks/{id}/test` | `ADMIN` | Dispatch signed test ping payload (`X-CloudSense-Signature: sha256=...`). |
| `GET` | `/api/webhooks/logs` | `ADMIN`, `AUDITOR` | Query webhook delivery audit logs and response codes. |
| `GET` | `/api/actions` | Authenticated | List automated remediation actions and statuses. |
| `POST` | `/api/actions/propose` | `ADMIN`, `FINOPS_ENGINEER` | Propose new remediation actions (defaults to `PROPOSED`). |
| `POST` | `/api/actions/{id}/approve` | `ADMIN`, `FINOPS_ENGINEER` | Approve and execute proposed remediation action. |
| `POST` | `/api/actions/{id}/reject` | `ADMIN`, `FINOPS_ENGINEER` | Reject proposed remediation action. |
| `POST` | `/api/actions/{id}/rollback` | `ADMIN` | Revert executed action using its mandatory `rollback_plan`. |

---

## 10. Identity, Collaboration & Audit Logs
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/settings/users` | Authenticated | List organization workspace members. |
| `POST` | `/api/settings/users/invite` | `ADMIN` | Invite new user with assigned role (`ADMIN`, `FINOPS_ENGINEER`, `AUDITOR`, `VIEWER`). |
| `PUT` | `/api/settings/users/{id}/role` | `ADMIN` | Update user role with last-active-admin protection. |
| `DELETE` | `/api/settings/users/{id}` | `ADMIN` | Deactivate workspace user. |
| `GET` | `/api/audit/logs` | `ADMIN`, `AUDITOR` | Query structured audit trail with action/status filters. |
| `GET` | `/api/settings/profile` | Authenticated | Retrieve organization profile and billing currency. |
| `PUT` | `/api/settings/profile` | `ADMIN` | Update organization profile, currency, and timezone. |
