# CloudSense AI - Enterprise Production Deployment & Load Balancing Guide

## High-Concurrency Architecture Overview

CloudSense AI is configured for enterprise-grade high concurrency, zero information leakage, and end-to-end encrypted HTTPS load balancing.

```
                    ┌─────────────────────────┐
                    │ Internet / Web Clients  │
                    └───────────┬─────────────┘
                                │  (Port 80 redirect -> 443 HTTPS)
                                ▼
         ┌─────────────────────────────────────────────────┐
         │       Nginx TLS Termination & Load Balancer     │
         │  - High-Burst Login Rate Limiting (40r/s + 80b) │
         │  - OWASP Strict-Transport-Security (HSTS)       │
         │  - Server Fingerprint Stripping (Zero Leakage)   │
         │  - Keepalive Connection Pooling (64 sockets)     │
         └─────────────┬─────────────────────┬─────────────┘
                       │                     │
          (least_conn) │                     │ (least_conn)
                       ▼                     ▼
        ┌───────────────────────┐   ┌───────────────────────┐
        │  Backend API Cluster  │   │ Next.js Web Cluster   │
        │  - backend_1:8000     │   │ - frontend_1:3000     │
        │  - backend_2:8000     │   │ - frontend_2:3000     │
        │  - backend_3:8000     │   └───────────────────────┘
        └───────────┬───────────┘
                    │ (WAL Mode, normal sync, 15,000ms busy timeout)
                    ▼
        ┌───────────────────────┐
        │ Persistent SQLite/DB  │
        └───────────────────────┘
```

---

## Key Security & Reliability Pillars

### 1. Zero Information & Number Leakage
- **Contact & Phone Number Scrubbing**: All phone numbers, mobile numbers, and telephone sequences are masked to `***-***-XXXX`.
- **Card & SSN Protection**: Credit and debit cards are masked to `****-****-****-XXXX`; SSNs are masked to `***-**-XXXX`.
- **AI Analyst Privacy Guardrail**: The AI assistant actively detects and rejects any prompt attempting to extract client or owner personal numbers, credentials, or user tables.
- **Error Exception Shielding**: Database exceptions, stack traces, and internal file paths are intercepted and replaced with safe, unique UUID `incident_id` logs.
- **Server Header Masking**: `Server`, `X-Powered-By`, and `X-Runtime` headers are completely removed.

### 2. High-Concurrency Simultaneous Logins
- **SQLite Write-Ahead Logging (WAL)**: `PRAGMA journal_mode = WAL` enables concurrent readers and writers without blocking.
- **15,000ms Busy Timeout**: Prevents `database is locked` errors during concurrent login audit log writes.
- **Rate Limit with Large Burst Queue**: Nginx allows up to 40 req/s with a burst allowance of 80 requests without delay, allowing crowds of users to authenticate simultaneously.

### 3. HTTPS & TLS Termination
- Modern TLSv1.2 & TLSv1.3 protocols.
- Automated HTTP (Port 80) -> HTTPS (Port 443) 301 redirection.
- `Strict-Transport-Security` (HSTS) with 1-year duration, subdomains, and preloading.
- Content Security Policy (CSP), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.

---

## Quick Start Commands

### 1. Generate SSL Certificates
```bash
./deploy/ssl/generate_ssl_certs.sh localhost
```

### 2. Launch Production Cluster
```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

### 3. Verify Health & Load Balancer
```bash
curl -k https://localhost/api/health
```
Output:
```json
{"status":"healthy","service":"cloudsense-api","timestamp":"2026-10-21T...","uptime_seconds":12.4}
```
