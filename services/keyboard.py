from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import types
from db.database import get_async_session
from db.models import DMARoles, DAMACompetency
from sqlalchemy.future import select as async_select
from services.logger import logger

def build_start_buttons() -> types.ReplyKeyboardMarkup:
    """Создает клавиатуру с начальными кнопками"""
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать тестирование"))
    builder.add(types.KeyboardButton(text="Админ"))
    return builder.as_markup(resize_keyboard=True)

async def build_roles_keyboard():
    async with get_async_session() as session:
        try:
            result = await session.execute(async_select(DMARoles.dama_role_name).distinct())
            roles = result.scalars().all()

            builder = ReplyKeyboardBuilder()
            for role in roles:
                builder.add(types.KeyboardButton(text=role))
            builder.adjust(2)
            return builder.as_markup(resize_keyboard=True)
        except Exception as e:
            logger.error(f"Ошибка при получении списка ролей: {e}")
            raise

async def build_competencies_keyboard(selected_role: str):
    async with get_async_session() as session:
        try:
            stmt = async_select(DAMACompetency.dama_competence_name).where(
                DAMACompetency.dama_role_name == selected_role
            ).distinct()
            result = await session.execute(stmt)
            competencies = result.scalars().all()

            builder = ReplyKeyboardBuilder()
            for comp in competencies:
                builder.add(types.KeyboardButton(text=comp))
            builder.adjust(2)
            return builder.as_markup(resize_keyboard=True)
        except Exception as e:
            logger.error(f"Ошибка при получении списка компетенций: {e}")
            raise

def build_start_test_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="✅ Начать тестирование"))
    return builder.as_markup(resize_keyboard=True)

def build_admin_keyboard():
    """Клавиатура админ-панели"""
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Список AI провайдеров"))
    builder.add(types.KeyboardButton(text="Добавить нового провайдера"))
    builder.add(types.KeyboardButton(text="Изменить температуру"))
    builder.add(types.KeyboardButton(text="Назад"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def build_back_to_providers_keyboard():
    """Inline клавиатура для возврата к списку провайдеров"""
    builder = InlineKeyboardBuilder()
    builder.button(text="← Назад к провайдерам", callback_data="list_creators")
    return builder.as_markup()


def build_ai_creators_keyboard(creators: list) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура с выбором AI провайдера"""
    buttons = []
    for creator in creators:
        buttons.append([InlineKeyboardButton(
            text=creator.name,
            callback_data=f"select_creator:{creator.id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_model_choice_keyboard(models):
    buttons = [
        [InlineKeyboardButton(text=model.name, callback_data=f"select_model:{model.id}")]
        for model in models
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
