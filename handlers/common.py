from aiogram import types, Router
from aiogram.filters import Command
from db.enums import UserRole
from db.database import get_async_session
from db.models import User
from services.logger import logger
from sqlalchemy import select
from aiogram.fsm.context import FSMContext
from services.keyboard import build_start_buttons
from services.user_utils import is_user_banned
from aiogram import F, Router

common_router = Router()


@common_router.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    if not message.from_user:
        await message.answer("Не удалось определить отправителя.")
        return

    if await is_user_banned(message.from_user.id):
        await message.answer("Вы заблокированы и не можете использовать бота.")
        return

    async with get_async_session() as session:
        try:
            await state.clear()
            
            result = await session.execute(select(User).where(User.id == message.from_user.id))
            existing_user = result.scalars().first()

            if existing_user and str(existing_user.role) == UserRole.BANNED:
                await message.answer("Вы заблокированы и не можете использовать бота.")
                return

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
                "Для начала тестирования компетенций DAMA нажмите кнопку ниже: ⬇️",
                reply_markup=build_start_buttons()
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при сохранении пользователя: {e}")
            await message.answer("Произошла ошибка при сохранении данных.")
