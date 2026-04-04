import asyncio
import sys
import asyncpg

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def test():
    conn = await asyncpg.connect(
        host="127.0.0.1",
        port=5432,
        user="admin",
        password="password123",
        database="linkup_app",
        ssl=False,
    )
    result = await conn.fetchval("SELECT 1")
    print("Success:", result)
    await conn.close()


asyncio.run(test())
