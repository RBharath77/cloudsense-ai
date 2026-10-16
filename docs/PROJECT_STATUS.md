# CloudSense AI — Project Status

Last Updated: Phase 1 Audit (Baseline)

## 1. System Inventory & Baseline Status

| Component | Status | Details |
|---|---|---|
| **Frontend UI** | Partially Functional | Next.js 15.4 / React 19 app with complete App Router pages for all main modules. `node_modules` is installed. |
| **Backend API** | Partially Functional | FastAPI with inline routes in `backend/app/main.py`. Database models and auth implemented. |
| **Database Schema** | Functional | SQLAlchemy ORM with 15 tables defined in `backend/app/models/__init__.py`. Supports PostgreSQL & SQLite fallback. |
| **Virtual Environment** | Needs Setup | `.venv` in workspace root is Python 3.14 without packages. Python 3.11/3.12 exists on macOS host with pre-built binary wheels for all requirements. |
| **Test Suite** | Untested / Blocked | Tests exist in `backend/tests/` (`test_auth.py`, `test_ml.py`). Blocked on dependencies being installed in `.venv`. |
| **Forecasting Module** | Broken (Bug Found) | NumPy broadcasting bug in `backend/app/ml.py` line 11 (`y - pred` where `y` is full length and `pred` is evaluation window). |
| **Dashboard Data Path** | Broken / Fragile | Root-cause identified: relative DB path causes empty database if started from different CWD; register creates empty org with 0 records; `spend` calculation not assigned to response. |
| **Git Version Control** | Uninitialized | Directory is not currently a git repository. Recommended to initialize `git init` locally to enable safe diffs and rollback tracking. |

## 2. Verified Root Causes

### Dashboard Zero-Value Issue
1. **Working Directory & Relative DB Path:** `Settings.database_url` defaults to `sqlite:///./cloudsense.db`. Seeding from `backend/` creates `backend/cloudsense.db`, but running uvicorn from workspace root opens `./cloudsense.db` (an empty, unseeded file).
2. **Multi-Tenant User Isolation:** When a user registers at `/api/auth/register`, a brand new organization is created without seeded resources or cost records. Only the seeded account `admin@cloudsense.ai` is linked to `NovaTech Solutions`.
3. **Data Mapping Inconsistency:** In `backend/app/main.py`, `spend` is queried over `CostRecord`, but is never returned in the `/api/dashboard/summary` dictionary; instead `total` (from `CloudResource.monthly_cost`) is used for both `total_spend` and `current_month_spend`.

### Forecasting Model Broadcast Failure
- In `backend/app/ml.py` line 11: `std = float(np.std(y - pred)) if len(pred) else 0`.
- `y` is the full time series (e.g. 30 days) and `pred` is evaluated only on `np.arange(split, len(y))` (e.g. 3 to 15 days). Subtracting unequal shapes throws `ValueError: operands could not be broadcast together`.
- Fix required: evaluate standard deviation against the actual ground truth slice: `np.std(y[split:] - pred)`.

## 3. High-Priority Next Actions (Phase 1 Scope)
1. Initialize local Git repository to preserve history and enable clean diffs.
2. Configure `.venv` with Python 3.11 and install `backend/requirements.txt`.
3. Fix the array dimension bug in `backend/app/ml.py`.
4. Fix the database path resolution in `backend/app/config.py` to use an absolute path or consistent anchor.
5. Fix the dashboard metric mapping in `backend/app/main.py`.
6. Run the test suite and verify all unit tests pass.
