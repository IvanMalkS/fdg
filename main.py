from bot.bot import init_bot
import asyncio
from db.database import init_db

async def main():
    await init_db()
    await init_bot()

if __name__ == "__main__":
    asyncio.run(main())
