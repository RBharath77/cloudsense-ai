# CloudSense AI — Project Status

Last Updated: Phase 7 Optimization, Savings Ledger, and What-If Simulator — COMPLETED

## 1. System Inventory & Verified Status

| Component | Status | Details |
|---|---|---|
| **Evidence-Backed Recommendation Engine** | Verified Working (Phase 7) | Telemetry-grounded recommendation service (`backend/app/services/optimization_service.py`) analyzing actual resource CPU/memory metrics and time-series. Enforces strict non-fabrication: zero utilization claims without real telemetry data. |
| **Multi-Objective Priority Scoring Engine** | Verified Working (Phase 7) | Transparent scoring engine supporting 4 selectable priorities (`BALANCE`, `COST`, `EMISSIONS`, `RISK_AVOIDANT`). Returns explicit scoring weights and formulas in API metadata. |
| **Read-Only What-If Scenario Simulator** | Verified Working (Phase 7) | Interactive scenario simulator supporting fleet rightsizing, off-hours shutdown schedules, 1-yr/3-yr Savings Plans, and green regional grid migration. Strictly read-only: records scenario inputs, pricing catalogs (AWS/Azure 2025), assumptions, and outputs in `SimulationScenario` without mutating live cloud resources. |
| **Verified Savings Ledger** | Verified Working (Phase 7) | Authoritative savings tracking model (`SavingsLedger`) distinguishing expected forecast savings from verified post-implementation measurements. Calculates realization rate (%), tracks measurement windows, and records operational caveats. |
| **Frontend UI (Optimization & Simulator)** | Verified Working (Phase 7) | Full-featured UI in `frontend/components/OptimizationEngine.tsx` and `frontend/app/optimization/page.tsx` featuring priority toggles with live weight badges, expandable evidence/assumptions accordion, interactive scenario what-if modeler with before/after comparisons, and verified savings ledger table. Next.js production build cleanly compiled (23/23 static pages). |
| **CarbonSense™ Intelligence Engine** | Verified Working (Phase 6) | Source-aware greenhouse gas accounting (`backend/app/services/carbon_service.py`) supporting Scope 1, Scope 2 (market/location-based), and Scope 3 classification per GHG Protocol. Evaluates footprint without deriving emissions from financial spend. |
| **Regional Grid Intensity Factors Registry** | Verified Working (Phase 6) | Authoritative factor registry citing published benchmarks (EPA eGRID 2024, EEA 2023, Fingrid) mapping regional intensity (gCO2e/kWh) and clean energy percentages across cloud regions. |
| **Multi-Horizon ML Forecasting Engine** | Verified Working (Phase 5) | Trend forecasting model (`backend/app/services/forecast_service.py` & `backend/app/ml.py`) supporting multi-horizon forecasting (7D–90D), provider filtering, dynamic confidence intervals (80%/95%), and non-negative clamping. |
| **Model Registry & Zero-Leakage Backtesting** | Verified Working (Phase 5) | Chronological backtest evaluation ($t < split$ train, $t \ge split$ test) evaluating MAE, RMSE, and benchmark comparison against a strict Naive Persistence Baseline (`improvement_pct`). |
| **Isolation Forest Anomaly Engine & RCA** | Verified Working (Phase 5) | Unsupervised anomaly detection (`backend/app/services/anomaly_service.py`) evaluating residual deviations against learned median envelopes with financial impact calculation and deterministic Root Cause Analysis. |
| **Persistent Budget Engine** | Verified Working (Phase 4) | Full CRUD service (`backend/app/services/budget_service.py`) supporting Organization, Provider, and Service scopes, configurable alert thresholds, live spend aggregation, and burn-rate projections. |
| **Deduplicated Alert Engine** | Verified Working (Phase 4) | Alert evaluation engine (`backend/app/services/alert_service.py`) with fingerprint-based SHA-256 deduplication: `sha256(org:entity:type:period)`. |
| **Tag Governance & Compliance** | Verified Working (Phase 4) | Resource compliance auditor (`backend/app/services/tag_governance.py`) checking resources against required tags (`Environment`, `Owner`, `CostCenter`, `Project`). |
| **Cost Aggregation & Explorer Service** | Verified Working (Phase 3) | Authoritative aggregation service (`backend/app/services/cost_aggregation.py`) providing multi-dimensional filtering, grouping, period-over-period comparison, and data lineage extraction. |
| **Reconciliation & Export Engine** | Verified Working (Phase 3) | Streaming CSV export endpoint (`/api/costs/export`) guaranteed to match API summary totals 100%. Sanitizes cells against formula injection (`=`, `+`, `-`, `@`, `\t`, `\r`). |
| **Billing Ingestion** | Verified Working (Phase 2) | Normalized, transactional CSV ingestion engine (`backend/app/services/billing_import.py`) with SHA-256 duplicate rejection and idempotency replay. |
| **Backend API** | Verified Working | FastAPI 0.116.1 running on Python 3.11.16 with tenant-scoped isolation. |
| **Test Suite** | Passing (57/57) | `pytest` passes 57/57 tests across all 9 test suites (`test_auth.py`, `test_billing_import.py`, `test_cost_explorer.py`, `test_budgets_alerts.py`, `test_dashboard.py`, `test_forecast_anomalies.py`, `test_carbonsense.py`, `test_ml.py`, and `test_optimization_simulator.py`). |
| **Git Version Control** | Active | Branch `phase-7-optimization-simulator` with clean diff. |

## 2. Optimization, Simulator & Ledger Invariants Verified

1. **Telemetry Grounding Invariant:** Every recommendation claiming underutilization or rightsizing is strictly verified against real `CloudResource` telemetry and `MetricRecord` time series (e.g. average CPU %, peak CPU %, sample count). Zero recommendations are manufactured without telemetry evidence.
2. **Defensible Cost & Carbon Modeling:** Cost savings reflect actual resource spend and rate sheets. Carbon reductions ($kgCO_2e$) are modeled strictly from hardware wattage deltas and published regional grid emission factors (EPA eGRID 2024 / EEA 2023), never financial spend multipliers.
3. **Read-Only Simulation Invariant:** The scenario what-if simulator never mutates live cloud resources, infrastructure configurations, or billing records. All simulation runs are recorded in `SimulationScenario` for audit and repeatable comparison.
4. **Expected vs. Verified Distinction:** The `SavingsLedger` enforces strict separation between forecasted *expected savings* and post-implementation *verified savings*, calculating realization rates ($\frac{\text{Verified}}{\text{Expected}}\%$) and tracking measurement windows and caveats.
5. **Multi-Tenant Isolation:** Recommendations, what-if simulations, and savings ledger entries are strictly partitioned by authenticated `organization_id`. Cross-tenant queries return 404. Empty organizations return clean empty datasets with zero errors.

## 3. Test Evidence

```
============================= test session starts ==============================
platform darwin -- Python 3.11.16, pytest-8.4.1, pluggy-1.7.0 -- /Users/BharathR/Downloads/cloudsense-ai/.venv/bin/python3.11
cachedir: .pytest_cache
rootdir: /Users/BharathR/Downloads/cloudsense-ai
configfile: pytest.ini
plugins: anyio-4.15.1
collected 57 items

backend/tests/test_auth.py::test_password_hash PASSED                    [  1%]
backend/tests/test_billing_import.py::test_valid_billing_csv_import PASSED [  3%]
backend/tests/test_billing_import.py::test_duplicate_file_rejection PASSED [  5%]
backend/tests/test_billing_import.py::test_idempotency_key_replay PASSED [  7%]
backend/tests/test_billing_import.py::test_invalid_rows_reporting_and_zero_partial_writes PASSED [  8%]
backend/tests/test_billing_import.py::test_empty_csv_rejection PASSED    [ 10%]
backend/tests/test_billing_import.py::test_missing_required_headers PASSED [ 12%]
backend/tests/test_billing_import.py::test_multi_tenant_isolation_billing_imports PASSED [ 14%]
backend/tests/test_budgets_alerts.py::test_budget_crud_lifecycle PASSED  [ 15%]
backend/tests/test_budgets_alerts.py::test_budget_validation_errors PASSED [ 17%]
backend/tests/test_budgets_alerts.py::test_budget_spend_evaluation_and_status_transitions PASSED [ 19%]
backend/tests/test_budgets_alerts.py::test_alert_evaluation_and_deduplication PASSED [ 21%]
backend/tests/test_budgets_alerts.py::test_alert_triage_workflows PASSED [ 22%]
backend/tests/test_budgets_alerts.py::test_tag_governance_and_resource_compliance PASSED [ 24%]
backend/tests/test_budgets_alerts.py::test_empty_organization_budgets_and_alerts PASSED [ 26%]
backend/tests/test_budgets_alerts.py::test_multi_tenant_isolation_budgets_alerts PASSED [ 28%]
backend/tests/test_carbonsense.py::test_carbon_summary_aggregation PASSED [ 29%]
backend/tests/test_carbonsense.py::test_carbon_records_filtering PASSED  [ 31%]
backend/tests/test_carbonsense.py::test_carbon_factors_registry PASSED   [ 33%]
backend/tests/test_carbonsense.py::test_carbon_csv_import_success PASSED [ 35%]
backend/tests/test_carbonsense.py::test_carbon_csv_import_validation_errors PASSED [ 36%]
backend/tests/test_carbonsense.py::test_carbon_budget_lifecycle_and_status_transitions PASSED [ 38%]
backend/tests/test_carbonsense.py::test_empty_organization_carbon_safety PASSED [ 40%]
backend/tests/test_carbonsense.py::test_multi_tenant_isolation_carbon PASSED [ 42%]
backend/tests/test_cost_explorer.py::test_reconciliation_invariant PASSED [ 43%]
backend/tests/test_cost_explorer.py::test_cost_filtering_and_grouping PASSED [ 45%]
backend/tests/test_cost_explorer.py::test_cost_data_lineage PASSED       [ 47%]
backend/tests/test_cost_explorer.py::test_formula_injection_sanitization_in_csv_export PASSED [ 49%]
backend/tests/test_cost_explorer.py::test_empty_org_costs_and_dashboard PASSED [ 50%]
backend/tests/test_cost_explorer.py::test_multi_tenant_isolation_costs PASSED [ 52%]
backend/tests/test_dashboard.py::test_health PASSED                      [ 54%]
backend/tests/test_dashboard.py::test_login_demo_user PASSED             [ 56%]
backend/tests/test_dashboard.py::test_dashboard_seeded_organization PASSED [ 57%]
backend/tests/test_dashboard.py::test_dashboard_empty_organization_regression PASSED [ 59%]
backend/tests/test_dashboard.py::test_forecast_endpoint PASSED           [ 61%]
backend/tests/test_forecast_anomalies.py::test_multi_horizon_forecasting PASSED [ 63%]
backend/tests/test_forecast_anomalies.py::test_forecasting_evaluation_metrics_and_baseline PASSED [ 64%]
backend/tests/test_forecast_anomalies.py::test_provider_filtered_forecasting PASSED [ 66%]
backend/tests/test_forecast_anomalies.py::test_empty_organization_forecast_graceful PASSED [ 68%]
backend/tests/test_forecast_anomalies.py::test_list_anomalies_and_filtering PASSED [ 70%]
backend/tests/test_forecast_anomalies.py::test_dynamic_anomaly_detection_execution PASSED [ 71%]
backend/tests/test_forecast_anomalies.py::test_root_cause_analysis_endpoint PASSED [ 73%]
backend/tests/test_forecast_anomalies.py::test_multi_tenant_isolation_forecast_and_anomalies PASSED [ 75%]
backend/tests/test_ml.py::test_forecast PASSED                           [ 77%]
backend/tests/test_ml.py::test_forecast_multiple_horizons PASSED         [ 78%]
backend/tests/test_ml.py::test_forecast_insufficient_data PASSED         [ 80%]
backend/tests/test_ml.py::test_anomaly PASSED                            [ 82%]
backend/tests/test_optimization_simulator.py::test_hardware_carbon_and_grid_factor_calculations PASSED [ 84%]
backend/tests/test_optimization_simulator.py::test_priority_score_weighting_transparency PASSED [ 85%]
backend/tests/test_optimization_simulator.py::test_recommendations_evidence_and_grounding PASSED [ 87%]
backend/tests/test_optimization_simulator.py::test_recommendation_detail_endpoint PASSED [ 89%]
backend/tests/test_optimization_simulator.py::test_priority_modes_switch PASSED [ 91%]
backend/tests/test_optimization_simulator.py::test_what_if_simulator_single_recommendation PASSED [ 92%]
backend/tests/test_optimization_simulator.py::test_what_if_simulator_custom_scenarios PASSED [ 94%]
backend/tests/test_optimization_simulator.py::test_savings_ledger_lifecycle_and_caveats PASSED [ 96%]
backend/tests/test_optimization_simulator.py::test_empty_organization_optimization PASSED [ 98%]
backend/tests/test_optimization_simulator.py::test_multi_tenant_isolation_optimization PASSED [100%]

======================= 57 passed, 10 warnings in 25.42s =======================
```

## 4. Next Phase: Phase 8 — Grounded AI Analyst and Reporting
- Target: Grounded AI Analyst querying allowlisted backend functions (zero generated arbitrary SQL or shell commands), server-side cross-workspace access denial, and database-reconciled executive reporting.
