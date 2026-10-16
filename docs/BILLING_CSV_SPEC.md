# CloudSense AI — Normalized Billing CSV Specification

## Overview
CloudSense AI supports importing cloud expenditure and usage records via standardized CSV files. The ingestion engine validates files line-by-line, prevents duplicate records, enforces idempotency, guarantees transactional integrity, and links costs to specific import history entries.

---

## 1. Supported CSV Schema

### Column Definitions

| Column Name | Required | Accepted Aliases | Type / Format | Example | Normalization Behavior |
|---|---|---|---|---|---|
| `date` | **Yes** | `recorded_at`, `timestamp` | ISO 8601, `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS` | `2026-03-15` | Parsed to UTC datetime |
| `provider` | **Yes** | `cloud_provider` | String | `AWS` | Trimmed, converted to uppercase |
| `service` | **Yes** | `service_name` | String | `EC2` | Trimmed string |
| `amount` | **Yes** | `cost`, `total_cost` | Decimal / Float $\ge 0.0$ | `145.50` | Strips currency symbols, validated $\ge 0$ |
| `region` | No | `location` | String | `us-east-1` | Defaults to `"global"` |
| `resource_id`| No | `resource` | String | `i-0123456789` | Defaults to `null` |
| `currency` | No | `currency_code` | 3-letter ISO code | `USD` | Defaults to `"USD"` |

---

## 2. Ingestion Rules & Invariants

1. **Transactional Guarantee:** Ingestion is fully atomic. If any row contains an invalid date, negative cost, or missing required field, the entire batch is rejected with line numbers and error reasons. **Zero partial writes** are committed to the cost ledger.
2. **Duplicate Prevention:** The ingestion engine computes a SHA-256 hash of the uploaded CSV contents. Re-uploading an identical file within the same organization returns status `DUPLICATE` without double-counting records.
3. **API Idempotency:** The `POST /api/billing/import` endpoint honors the `Idempotency-Key` HTTP header. Re-transmitting the same key replays the original result without executing duplicate database inserts.
4. **Multi-Tenant Isolation:** All records and import histories are strictly partitioned by `organization_id`. A user from Organization A can never view or overwrite billing data belonging to Organization B.

---

## 3. Sample CSV

```csv
date,provider,service,amount,region,resource_id,currency
2026-03-01,AWS,EC2,150.50,us-east-1,i-12345678,USD
2026-03-02,Azure,Virtual Machines,85.25,eastus,vm-001,USD
2026-03-03,GCP,Compute Engine,42.10,us-central1,inst-999,USD
```

---

## 4. API Endpoints

### Upload Billing CSV
- **Endpoint:** `POST /api/billing/import`
- **Headers:**
  - `Authorization: Bearer <token>`
  - `Idempotency-Key: <optional-unique-key>`
- **Body:** `multipart/form-data` with `file: <csv-file>`
- **Success Response (201 Created):**
  ```json
  {
    "import_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "COMPLETED",
    "message": "Successfully imported 3 billing record(s).",
    "total_rows": 3,
    "imported_rows": 3,
    "error_count": 0,
    "errors": []
  }
  ```
- **Error Response (400 Bad Request):**
  ```json
  {
    "import_id": "c1f7b029-2169-4509-90d5-b6d85942475e",
    "status": "FAILED",
    "message": "Import rejected with 2 validation error(s). Zero records were inserted.",
    "total_rows": 4,
    "imported_rows": 0,
    "error_count": 2,
    "errors": [
      {
        "line": 3,
        "error": "Invalid date '2026-99-99'. Expected format YYYY-MM-DD or ISO 8601."
      },
      {
        "line": 5,
        "error": "Invalid amount '-50.00'. Amount must be a non-negative number."
      }
    ]
  }
  ```

### List Import History
- **Endpoint:** `GET /api/billing/imports`
- **Returns:** List of past imports with status, row counts, and timestamps.

### Import Details
- **Endpoint:** `GET /api/billing/imports/{id}`
- **Returns:** Full metadata and line-by-line error details for debugging failed uploads.
