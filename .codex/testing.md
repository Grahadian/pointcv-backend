# Testing Rules

## Backend
- Test all service functions
- Test all API endpoints (happy path + error cases)
- Mock external services (Midtrans, R2)
- Use pytest + pytest-asyncio
- Target: 80% coverage minimum

## Frontend
- Test critical user flows
- Test form validation
- Test payment integration (mock Midtrans)
- Use Vitest + React Testing Library

## Before Commit
- All tests must pass
- No TypeScript errors
- No ESLint warnings
