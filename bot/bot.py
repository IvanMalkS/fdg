from config import Config
from aiogram import Bot, Dispatcher
from services.state_service import state_storage
from services.middleware import BanCheckMiddleware

from handlers.test_handlers import test_router
from handlers.admin_hendler import admin_router
from aiogram.client.default import DefaultBotProperties
from handlers.common import common_router

def setup_handlers(dp: Dispatcher) -> None:
    dp.include_router(common_router)
    dp.include_router(test_router)
    dp.include_router(admin_router)

async def init_bot() -> None:
    """Initialize bot"""
    bot = Bot(token=Config.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    
    storage = await state_storage.get_storage()
    dp = Dispatcher(storage=storage)

    # Setup middleware
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    setup_handlers(dp)

    await dp.start_polling(bot)
