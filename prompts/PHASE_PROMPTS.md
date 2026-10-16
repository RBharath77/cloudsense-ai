# CloudSense AI — Phase Prompts and Acceptance Tests

Use one prompt per task. Each prompt assumes the workspace rules, product scope, and start/finish skills are active. Begin each phase with a plan and approval; then implement only the approved scope.

## Phase 1 — Audit and stabilize
Use the Phase 1 prompt in `MASTER_PROMPT.md`. Do not begin later phases until the dashboard/prediction audit is complete and the baseline is documented.

## Phase 2 — Data foundation and billing import
Goal: implement or repair a normalized, validated, idempotent billing import path.

## Phase 3 — Dashboard, Cost Explorer, and lineage
Goal: use one backend aggregation service for dashboard cards, charts, tables, and exports.

## Phase 4 — Budgets, alerts, and tag governance
Goal: implement persistent budgets and a deduplicated alert engine using actual cost records.

## Phase 5 — Forecasts, model registry, backtesting, anomalies
Goal: forecasting quality and anomaly detection with baseline comparisons and no data leakage.

## Phase 6 — CarbonSense and emissions data provenance
Goal: build source-aware emissions tracking without inventing environmental data.

## Phase 7 — Optimization, savings ledger, and simulator
Goal: offer evidence-backed recommendations and scenario estimates without altering live cloud resources.

## Phase 8 — AI Analyst, reports, and executive digest
Goal: answer supported questions using safe backend tools and generate reports that reconcile with the database.

## Phase 9 — Security, identity, and collaboration
Goal: enforce strict tenant isolation, authorization, and audit logs.

## Phase 10 — One provider connector
Goal: integrate the first live read-only cloud provider adapter with fixtures.

## Phase 11 — Background jobs and DevOps
Goal: reliable job execution, health checks, migrations, and observability.

## Phase 12 — Optional advanced features
Goal: select independent high-value extensions (e.g. Terraform plan cost/carbon estimator, Kubernetes cost allocation).

## Phase 13 — Release readiness
Goal: verify clean installation, test suite passes, documentation matches code, and zero secrets committed.
