import asyncio

from app.database import get_db_sessionmaker
from app.seed import seed_data


async def main() -> None:
    session = get_db_sessionmaker()()
    try:
        await seed_data(session)
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
