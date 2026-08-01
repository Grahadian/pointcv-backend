# TDD Workflow for PointCV

## Cycle: RED -> GREEN -> REFACTOR

1. RED: Write failing test
   - Define expected behavior
   - Run test -> should fail

2. GREEN: Write minimal code to pass
   - Implement just enough
   - Run test -> should pass

3. REFACTOR: Clean up
   - Improve code quality
   - Run test -> still pass

## Test Priority
1. Payment flow (critical)
2. Authentication (critical)
3. Order CRUD (high)
4. File upload (high)
5. Admin operations (medium)
6. Public pages (low)
