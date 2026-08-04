# PointCV - Claude Code Project Config

## Project Overview
PointCV is a professional CV creation service with 3 packages (Basic, Professional, Premium),
3 CV templates (Modern, Classic, ATS-Friendly), bilingual support (ID/EN), 
Midtrans payment, Cloudflare R2 file storage, and real-time progress tracking.

## Tech Stack
- Frontend: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
- Auth: Better Auth (self-hosted; HS256 JWT shared-secret verification)
- Backend: FastAPI + Python 3.11 + SQLAlchemy 2.0 async
- Database: SQLite (dev) → Neon PostgreSQL (prod)
- Storage: Cloudflare R2 (presigned URLs)
- Payment: Midtrans Snap API
- Deploy: Vercel (frontend) + Render/Fly.io (backend)

## Architecture Rules
1. Backend: Business logic ONLY in services/. Routers are thin.
2. Backend: Max 200 lines per file. Split if larger.
3. Backend: All env vars via pydantic-settings. No hardcoded secrets.
4. Backend: JWT verification mandatory on protected routes.
5. Frontend: Server Components by default. 'use client' only when needed.
6. Frontend: Use shadcn/ui components. No external UI libraries.
7. Frontend: Bilingual support via JSON files (lib/i18n/).
8. Both: Type safety mandatory. No `any` in TS, type hints in Python.

## Current Status
- Phase: Auth migrated from Clerk to Better Auth
- Auth: Verifies HS256 JWTs issued by the frontend using the shared `BETTER_AUTH_SECRET`; user row auto-created on first request (first user becomes admin)

## Environment Variables
### Backend (.env)
DATABASE_URL=sqlite+aiosqlite:///./pointcv.db
BETTER_AUTH_SECRET=shared_secret_matching_frontend
BETTER_AUTH_URL=http://localhost:3000
MIDTRANS_SERVER_KEY=SB-Mid-server-xxx
MIDTRANS_CLIENT_KEY=SB-Mid-client-xxx
MIDTRANS_IS_PRODUCTION=false
R2_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=pointcv-files
R2_PUBLIC_URL=https://pub-xxx.r2.dev

### Frontend (.env.local)
BETTER_AUTH_SECRET=must_match_backend
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
