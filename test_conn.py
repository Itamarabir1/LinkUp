import asyncio 
import asyncpg 
async def test(): 
    conn = await asyncpg.connect('postgresql://admin:password123@localhost:5432/linkup_app') 
    result = await conn.fetchval('SELECT 1') 
    print('Success:', result) 
    await conn.close() 
asyncio.run(test()) 
