# Security
Passwords are hashed; API access is JWT-protected; provider credentials are not sent to the frontend. Real infrastructure mutation is intentionally not automatic. Use environment variables/secrets management in production, rotate demo credentials, enforce HTTPS, configure restrictive CORS, add rate limiting, and use managed secret storage.
