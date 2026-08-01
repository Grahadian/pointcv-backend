# Coding Style Rules (MANDATORY)

## File Organization
- MAX 200 lines per file. Split if larger.
- One class/component per file (except small utilities)
- Group related files in folders

## Python (Backend)
- Use type hints everywhere
- Async/await for all I/O operations
- Business logic ONLY in services/
- Routers ONLY: receive request -> call service -> return response
- No database queries in routers
- Use Pydantic v2 for all request/response models
- Use SQLAlchemy 2.0 async patterns
- Function names: snake_case
- Class names: PascalCase
- Constants: UPPER_SNAKE_CASE

## TypeScript (Frontend)
- Strict TypeScript mode
- Use interfaces for data models
- Use types for unions/utility
- Component names: PascalCase
- Function names: camelCase
- Hook names: useCamelCase
- File names: kebab-case
- No `any` type (use `unknown` if necessary)

## Imports
- Group: external -> internal -> relative
- Sort alphabetically within groups
- No unused imports

## Error Handling
- Backend: Use custom HTTP exceptions with proper status codes
- Frontend: Use error boundaries + toast notifications
- NEVER swallow errors silently
- Log errors with context (user_id, endpoint, payload)
