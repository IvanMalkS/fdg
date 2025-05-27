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
    builder.add(types.KeyboardButton(text="Изменить промпт"))
    builder.add(types.KeyboardButton(text="Список пользователей"))
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


def build_users_keyboard(users: list, page: int, page_size: int = 10):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for user in users:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{user.id} - {user.username or 'No username'}",
                callback_data=f"select_user:{user.id}"
            )
        ])
    
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"users_page:{page - 1}"
        ))
    if len(users) == page_size:
        pagination_row.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"users_page:{page + 1}"
        ))
    
    if pagination_row:
        keyboard.inline_keyboard.append(pagination_row)
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_admin"
        )
    ])
    
    return keyboard
