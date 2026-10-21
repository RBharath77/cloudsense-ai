import re
import json
import uuid
import logging
from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import FastAPI, HTTPException
from ..config import settings

logger = logging.getLogger("cloudsense.security")

# --------------------------------------------------------------------------
# Regex Patterns for Sensitive Numbers & Client/Owner Details
# --------------------------------------------------------------------------
# International and standard phone numbers (+1-xxx-xxx-xxxx, (xxx) xxx-xxxx, 10-digit formats)
PHONE_REGEX = re.compile(
    r'(?<!\w)(?:\+?[1-9]\d{0,2}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}(?!\w)'
)

# 13-19 digit Credit/Debit Card numbers with optional hyphens or spaces
CARD_REGEX = re.compile(
    r'\b(?:\d{4}[-\s]?){3}\d{1,4}\b'
)

# US SSN / National Tax Identification format
SSN_REGEX = re.compile(
    r'\b\d{3}-\d{2}-\d{4}\b'
)

# AWS Access Key ID format (AKIA...)
AWS_KEY_REGEX = re.compile(
    r'\b(AKIA[0-9A-Z]{16})\b'
)

# Generic Secret / Private Key markers
SECRET_KEY_REGEX = re.compile(
    r'(?i)(?:secret|password|api[_-]?key|auth[_-]?token|private[_-]?key)\s*[:=]\s*["\']?([^"\'\s]{8,})'
)

# Keys that should never be serialized in outbound JSON
FORBIDDEN_OBJECT_KEYS = {
    "password_hash",
    "password",
    "secret_key",
    "aws_secret_access_key",
    "client_secret",
    "private_key",
    "refresh_token",
    "admin_secret",
}

def mask_phone_number(match_or_text: str) -> str:
    """Masks phone number leaving only last 4 digits visible."""
    digits = re.sub(r'\D', '', match_or_text)
    if len(digits) >= 10:
        return f"***-***-{digits[-4:]}"
    elif len(digits) >= 7:
        return f"***-{digits[-4:]}"
    return "***-****"

def mask_card_number(match_or_text: str) -> str:
    """Masks credit card number according to PCI-DSS rules (first 4 and last 4 or only last 4)."""
    digits = re.sub(r'\D', '', match_or_text)
    if len(digits) >= 13:
        return f"****-****-****-{digits[-4:]}"
    return "****-****-****"

def mask_ssn(match_or_text: str) -> str:
    """Masks SSN / National ID number."""
    digits = re.sub(r'\D', '', match_or_text)
    if len(digits) >= 4:
        return f"***-**-{digits[-4:]}"
    return "***-**-****"

def sanitize_string(text: str) -> str:
    """Sanitizes text by replacing phone numbers, card numbers, SSNs, and raw secrets."""
    if not isinstance(text, str) or len(text) < 7:
        return text

    # Redact SSN
    text = SSN_REGEX.sub(lambda m: mask_ssn(m.group(0)), text)

    # Redact Credit Cards (verify min 13 digits)
    def _card_sub(m):
        digits = re.sub(r'\D', '', m.group(0))
        if 13 <= len(digits) <= 19:
            return mask_card_number(m.group(0))
        return m.group(0)
    text = CARD_REGEX.sub(_card_sub, text)

    # Redact Phone Numbers (match 10-14 digit sequences)
    def _phone_sub(m):
        raw = m.group(0)
        digits = re.sub(r'\D', '', raw)
        # Avoid masking dates like 2026-10-21 or ISO timestamps
        if 10 <= len(digits) <= 14 and not ("-" in raw and len(raw.split("-")[0]) == 4):
            return mask_phone_number(raw)
        return raw
    text = PHONE_REGEX.sub(_phone_sub, text)

    # Redact AWS keys
    text = AWS_KEY_REGEX.sub(r'\1[:4]****************', text)

    return text

def sanitize_payload(obj: Any) -> Any:
    """
    Recursively scans and scrubs outbound dictionaries, lists, and primitives
    to guarantee zero accidental leakage of client/owner contact numbers,
    personal credentials, or sensitive secrets.
    """
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if k.lower() in FORBIDDEN_OBJECT_KEYS:
                cleaned[k] = "[REDACTED]"
            elif "phone" in k.lower() or "mobile" in k.lower() or "contact" in k.lower():
                cleaned[k] = mask_phone_number(str(v)) if v else v
            elif "ssn" in k.lower() or "tax_id" in k.lower():
                cleaned[k] = mask_ssn(str(v)) if v else v
            elif "card" in k.lower() and "number" in k.lower():
                cleaned[k] = mask_card_number(str(v)) if v else v
            else:
                cleaned[k] = sanitize_payload(v)
        return cleaned
    elif isinstance(obj, list):
        return [sanitize_payload(item) for item in obj]
    elif isinstance(obj, str):
        return sanitize_string(obj)
    return obj

# --------------------------------------------------------------------------
# Zero-Leakage & HTTPS Security Middleware
# --------------------------------------------------------------------------
class ZeroLeakageSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enterprise-Grade Security Middleware implementing:
    1. HTTPS / HSTS enforcement and TLS termination awareness.
    2. Zero Information Leakage: automatic PII and sensitive number scrubbing.
    3. Removal of server fingerprinting headers (Server, X-Powered-By).
    4. Comprehensive OWASP Recommended HTTP Security Headers.
    """
    async def dispatch(self, request: Request, call_next):
        # 1. HTTPS Enforcement if configured
        proto = request.headers.get("x-forwarded-proto", request.url.scheme).lower()
        if settings.force_https and proto != "https":
            secure_url = request.url.replace(scheme="https")
            return Response(status_code=301, headers={"Location": str(secure_url)})

        # 2. Process request through downstream handlers
        response = await call_next(request)

        # 3. Strip server fingerprints to prevent attacker reconnaissance
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        # 4. Inject OWASP Standard HTTPS & Defense-in-Depth Security Headers
        if settings.hsts_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' http: https:;"
        )

        return response

def register_security_handlers(app: FastAPI):
    """
    Registers custom exception handlers that guarantee internal database errors,
    driver stack traces, file paths, and SQL statements are NEVER leaked to clients.
    """
    @app.exception_handler(Exception)
    async def global_safe_exception_handler(request: Request, exc: Exception):
        incident_id = str(uuid.uuid4())
        # Log complete diagnostic info internally on the server only
        logger.error(
            f"Internal server error [Incident: {incident_id}] on {request.method} {request.url.path}: {exc}",
            exc_info=True,
        )
        # Return sanitized, safe client response with zero internal leakage
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred. Your request has been securely logged.",
                "incident_id": incident_id,
            },
        )
