import csv
import io
import json
import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models import BillingImport, CostRecord

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
]

def parse_date(raw_date: str) -> datetime | None:
    if not raw_date:
        return None
    raw = raw_date.strip()
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None

def parse_and_validate_csv(content: bytes) -> tuple[list[dict], list[dict]]:
    if len(content) > MAX_FILE_SIZE:
        return [], [{"line": 1, "error": f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB."}]
    
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [{"line": 1, "error": "Invalid file encoding: CSV must be encoded in UTF-8."}]
    
    if not text.strip():
        return [], [{"line": 1, "error": "CSV file is empty."}]
    
    reader = csv.reader(io.StringIO(text))
    try:
        header_row = next(reader)
    except StopIteration:
        return [], [{"line": 1, "error": "CSV file contains no headers."}]
    
    headers = [h.strip().lower() for h in header_row]
    col_map: dict[str, int] = {}
    for idx, h in enumerate(headers):
        if h in ("date", "recorded_at", "timestamp"):
            col_map["date"] = idx
        elif h in ("provider", "cloud_provider"):
            col_map["provider"] = idx
        elif h in ("service", "service_name"):
            col_map["service"] = idx
        elif h in ("amount", "cost", "total_cost"):
            col_map["amount"] = idx
        elif h in ("region", "location"):
            col_map["region"] = idx
        elif h in ("resource_id", "resource"):
            col_map["resource_id"] = idx
        elif h in ("currency", "currency_code"):
            col_map["currency"] = idx
    
    missing_required = []
    for req in ("date", "provider", "service", "amount"):
        if req not in col_map:
            missing_required.append(req)
    if missing_required:
        return [], [{"line": 1, "error": f"Missing required column(s): {', '.join(missing_required)}."}]
    
    valid_rows: list[dict] = []
    errors: list[dict] = []
    line_number = 1  # header is line 1
    
    for row in reader:
        line_number += 1
        if not row or all(c.strip() == "" for c in row):
            continue  # skip blank lines
        
        # Check column count
        if len(row) <= max(col_map.values()):
            errors.append({
                "line": line_number,
                "error": f"Malformed row: expected at least {max(col_map.values()) + 1} columns, got {len(row)}."
            })
            continue
        
        # Validate date
        raw_date = row[col_map["date"]].strip()
        parsed_dt = parse_date(raw_date)
        if parsed_dt is None:
            errors.append({
                "line": line_number,
                "error": f"Invalid date '{raw_date}'. Expected format YYYY-MM-DD or ISO 8601."
            })
            continue
        
        # Validate provider
        raw_provider = row[col_map["provider"]].strip()
        if not raw_provider:
            errors.append({
                "line": line_number,
                "error": "Missing or empty required field 'provider'."
            })
            continue
        provider = raw_provider.upper()
        
        # Validate service
        service = row[col_map["service"]].strip()
        if not service:
            errors.append({
                "line": line_number,
                "error": "Missing or empty required field 'service'."
            })
            continue
        
        # Validate amount
        raw_amount = row[col_map["amount"]].strip().replace("$", "").replace(",", "")
        try:
            amount = float(raw_amount)
            if amount < 0 or amount != amount:  # check NaN
                errors.append({
                    "line": line_number,
                    "error": f"Invalid amount '{raw_amount}'. Amount must be a non-negative number."
                })
                continue
        except ValueError:
            errors.append({
                "line": line_number,
                "error": f"Invalid amount '{raw_amount}'. Must be a valid numeric value."
            })
            continue
        
        # Optional fields
        region = row[col_map["region"]].strip() if "region" in col_map else "global"
        if not region:
            region = "global"
            
        resource_id = row[col_map["resource_id"]].strip() if "resource_id" in col_map else None
        if not resource_id:
            resource_id = None
            
        currency = row[col_map["currency"]].strip().upper() if "currency" in col_map else "USD"
        if not currency or len(currency) != 3:
            currency = "USD"
        
        valid_rows.append({
            "recorded_at": parsed_dt,
            "provider": provider,
            "service": service,
            "amount": round(amount, 4),
            "region": region,
            "resource_id": resource_id,
            "currency": currency,
        })
    
    if not valid_rows and not errors:
        errors.append({"line": 1, "error": "CSV contains no data rows."})
        
    return valid_rows, errors

def process_billing_csv(
    db: Session,
    organization_id: str,
    user_id: str | None,
    filename: str,
    content: bytes,
    idempotency_key: str | None = None
) -> dict:
    file_hash = hashlib.sha256(content).hexdigest()
    
    # 1. Idempotency Key Replay Check
    if idempotency_key:
        existing = db.query(BillingImport).filter_by(
            organization_id=organization_id,
            idempotency_key=idempotency_key
        ).first()
        if existing:
            errs = json.loads(existing.errors_summary) if existing.errors_summary else []
            return {
                "import_id": existing.id,
                "status": existing.status,
                "message": "Idempotent request: returning previous import result.",
                "idempotent_replay": True,
                "total_rows": existing.total_rows,
                "imported_rows": existing.imported_rows,
                "error_count": existing.error_count,
                "errors": errs,
                "created_at": existing.created_at.isoformat(),
            }
    
    # 2. Duplicate Exact File Check
    duplicate_file = db.query(BillingImport).filter_by(
        organization_id=organization_id,
        file_hash=file_hash,
        status="COMPLETED"
    ).first()
    if duplicate_file:
        return {
            "import_id": duplicate_file.id,
            "status": "DUPLICATE",
            "message": f"Duplicate file detected: exact file contents were already imported at {duplicate_file.created_at.strftime('%Y-%m-%d %H:%M:%S')}. Records were not double-counted.",
            "duplicate": True,
            "total_rows": duplicate_file.total_rows,
            "imported_rows": 0,
            "error_count": 0,
            "errors": [],
            "created_at": duplicate_file.created_at.isoformat(),
        }
    
    # 3. Parse and validate CSV
    valid_rows, errors = parse_and_validate_csv(content)
    total_count = len(valid_rows) + len(errors)
    
    import_rec = BillingImport(
        organization_id=organization_id,
        user_id=user_id,
        filename=filename,
        file_hash=file_hash,
        idempotency_key=idempotency_key,
        total_rows=total_count,
        created_at=datetime.utcnow()
    )
    db.add(import_rec)
    db.flush()  # get import_rec.id
    
    # 4. Transactional enforcement: if any errors exist, rollback cost records and record failure
    if errors:
        import_rec.status = "FAILED"
        import_rec.error_count = len(errors)
        import_rec.imported_rows = 0
        import_rec.errors_summary = json.dumps(errors)
        import_rec.completed_at = datetime.utcnow()
        db.commit()
        return {
            "import_id": import_rec.id,
            "status": "FAILED",
            "message": f"Import rejected with {len(errors)} validation error(s). Zero records were inserted.",
            "total_rows": total_count,
            "imported_rows": 0,
            "error_count": len(errors),
            "errors": errors,
            "created_at": import_rec.created_at.isoformat(),
        }
    
    # 5. Insert all normalized cost records
    for row in valid_rows:
        cost = CostRecord(
            organization_id=organization_id,
            provider=row["provider"],
            service=row["service"],
            region=row["region"],
            resource_id=row["resource_id"],
            amount=row["amount"],
            recorded_at=row["recorded_at"],
            currency=row["currency"],
            import_id=import_rec.id,
        )
        db.add(cost)
    
    import_rec.status = "COMPLETED"
    import_rec.imported_rows = len(valid_rows)
    import_rec.error_count = 0
    import_rec.completed_at = datetime.utcnow()
    db.commit()
    
    return {
        "import_id": import_rec.id,
        "status": "COMPLETED",
        "message": f"Successfully imported {len(valid_rows)} billing record(s).",
        "total_rows": len(valid_rows),
        "imported_rows": len(valid_rows),
        "error_count": 0,
        "errors": [],
        "created_at": import_rec.created_at.isoformat(),
    }
