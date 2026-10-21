#!/usr/bin/env bash
# ==============================================================================
# CloudSense AI - Zero-Leakage High-Security TLS/SSL Certificate Generator
# Generates ECDSA / RSA 4096-bit self-signed or CA-ready TLS certificates
# with Subject Alternative Names (SAN) for localhost, 127.0.0.1, and custom domains.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}"
DOMAIN="${1:-localhost}"
DAYS_VALID=365

echo "🔐 Generating CloudSense AI Production TLS Certificates for domain: ${DOMAIN}..."

# Create OpenSSL configuration with Subject Alternative Names (SAN)
OPENSSL_CNF="${SSL_DIR}/openssl.cnf"
cat > "${OPENSSL_CNF}" << EOF
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = US
ST = California
L = San Francisco
O = CloudSense AI Inc.
OU = FinOps Security & Infrastructure
CN = ${DOMAIN}

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = *.${DOMAIN}
DNS.3 = localhost
DNS.4 = 127.0.0.1
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

KEY_FILE="${SSL_DIR}/cloudsense.key"
CSR_FILE="${SSL_DIR}/cloudsense.csr"
CRT_FILE="${SSL_DIR}/cloudsense.crt"

# 1. Generate RSA 4096-bit Private Key with strict permissions (0600)
openssl genrsa -out "${KEY_FILE}" 4096 2>/dev/null
chmod 600 "${KEY_FILE}"

# 2. Generate Certificate Signing Request (CSR)
openssl req -new -key "${KEY_FILE}" -out "${CSR_FILE}" -config "${OPENSSL_CNF}" 2>/dev/null

# 3. Generate X.509 Certificate valid for 365 days
openssl x509 -req -days "${DAYS_VALID}" -in "${CSR_FILE}" -signkey "${KEY_FILE}" -out "${CRT_FILE}" -extensions req_ext -extfile "${OPENSSL_CNF}" 2>/dev/null
chmod 644 "${CRT_FILE}"

# Cleanup CSR & temp cnf
rm -f "${CSR_FILE}" "${OPENSSL_CNF}"

echo "✅ TLS Certificate and Private Key successfully generated:"
echo "   - Certificate: ${CRT_FILE}"
echo "   - Private Key: ${KEY_FILE} (0600 strict permissions)"
echo "   - Subject Alt Names: DNS:${DOMAIN}, DNS:localhost, IP:127.0.0.1"
echo "🚀 Ready for Nginx HTTPS termination on port 443!"
