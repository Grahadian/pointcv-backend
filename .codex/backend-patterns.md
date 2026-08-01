# Backend Patterns for PointCV

## FastAPI Project Structure
```
app/
  main.py              # Entry point, lifespan, middleware
  config.py            # Pydantic Settings, env vars
  database.py          # SQLAlchemy async engine, session, Base
  dependencies.py      # Auth deps, DB deps, admin deps
  models/              # SQLAlchemy models
  schemas/             # Pydantic DTOs
  routers/             # Route definitions ONLY
  services/            # Business logic
```

## Router Pattern
```python
@router.post("", response_model=OrderResponse)
async def create_order(
    data: OrderCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    return await order_service.create(db, user_id, data)
```

## Service Pattern
```python
async def create(db: AsyncSession, user_id: str, data: OrderCreate):
    # Validation
    # Business logic
    # Database operation
    # Return result
```

## Error Pattern
```python
class PointCVException(HTTPException):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(status_code=status, detail={"code": code, "message": message})
```

## Async Database Pattern
```python
async with db.begin():
    result = await db.execute(query)
    return result.scalar_one_or_none()
```
