# Security Rules (MANDATORY)

## Authentication
- NEVER hardcode API keys, secrets, or tokens in source code
- ALL secrets must come from environment variables via pydantic-settings
- Better Auth JWT (HS256, shared secret) must be verified on EVERY protected endpoint
- Webhook endpoints must verify signature (Midtrans: SHA512)

## File Upload
- NEVER expose R2/S3 credentials to frontend
- ALWAYS use presigned URLs for file uploads
- Validate file type against whitelist: PHOTO, CERTIFICATE, DIPLOMA, DOCUMENT, RESULT_PDF
- Validate file size: max 5MB for images, 10MB for documents
- Validate mime type matches file extension
- Sanitize filename before storage

## Payment
- NEVER expose Midtrans Server Key to frontend
- ALWAYS verify Midtrans webhook signature
- Idempotent webhook handling: same notification processed once
- Log all payment events for audit

## Database
- NEVER construct SQL queries with string concatenation
- ALWAYS use parameterized queries (SQLAlchemy ORM)
- Sanitize all user inputs before database operations

## General
- No console.log in production code (use proper logging)
- Rate limit sensitive endpoints (payment, upload)
- CORS must specify exact origins, not wildcard (*)
