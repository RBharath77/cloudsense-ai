# Cloud Integration
`CloudProvider` defines cost/resources/metrics/events/security/billing boundaries. Mock, AWS, Azure and GCP adapters are intentionally isolated. Production adapters should use least-privilege IAM/service principals and server-side secret storage.
