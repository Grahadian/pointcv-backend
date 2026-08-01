---
name: security-review
description: Security-focused code review
---

Perform security audit on the code:

1. Authentication: Is JWT properly verified? Are routes protected?
2. Authorization: Is admin check enforced? Is ownership verified?
3. Input Validation: Are all inputs validated? Sanitized?
4. File Upload: Presigned URL? Type validation? Size limit?
5. Payment: Webhook signature verified? Idempotent?
6. Secrets: Any hardcoded keys? Env vars properly used?
7. SQL Injection: Parameterized queries? ORM usage?
8. XSS: Output encoding? Content Security Policy?

Flag ANY security issue as CRITICAL, HIGH, MEDIUM, or LOW.
