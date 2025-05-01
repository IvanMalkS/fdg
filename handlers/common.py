from aiogram import types, Router
from aiogram.filters import Command

from db.database import get_async_session
from db.models import User
from services.logger import logger
from sqlalchemy import select
from aiogram.fsm.context import FSMContext
from services.keyboard import build_start_buttons

common_router = Router()

@common_router.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    async with get_async_session() as session:
        try:
            await state.clear()
            
            result = await session.execute(select(User).where(User.id == message.from_user.id))
            existing_user = result.scalars().first()

            if not existing_user:
                new_user = User(
                    id=message.from_user.id,
                    first_name=message.from_user.first_name or '',
                    last_name=message.from_user.last_name or '',
                    username=message.from_user.username or '',
                    role='user'
                )
                session.add(new_user)
                await session.commit()
                welcome_message = "Привет! Твой профиль создан в системе."
            else:
                welcome_message = "С возвращением! Твой профиль уже есть в системе."

            await message.answer(
                f"{welcome_message}\n\n"
                "Для начала тестирования компетенций DAMA нажмите кнопку ниже:",
                reply_markup=build_start_buttons()
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при сохранении пользователя: {e}")
            await message.answer("Произошла ошибка при сохранении данных.")