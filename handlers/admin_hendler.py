from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, message
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from sqlalchemy import update
from aiogram.types import Message, InaccessibleMessage
from config import Config
from db.models import AiCreators, Models, AiSettings, User
from db.database import get_async_session, load_models
from handlers.states import AdminStates
from services.keyboard import build_ai_creators_keyboard, build_admin_keyboard, build_model_choice_keyboard, \
    build_back_to_providers_keyboard, build_users_keyboard
from services.redis_service import RedisService
from services.logger import logger
from db.enums import UserRole
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.user_utils import is_user_banned

admin_router = Router()
redis_service = RedisService()

@admin_router.message(F.text == "Админ")
async def admin_panel(message: Message, state: FSMContext):
    """Административная панель"""
    if message and message.from_user and await is_user_banned(message.from_user.id):
        await message.answer("Вы заблокированы и не можете использовать бота.")
        return

    if not await is_admin(message, state=state):
        await message.answer("У вас нет прав администратора")
        return

    await message.answer(
        "Админ-панель управления AI-провайдерами",
        reply_markup=build_admin_keyboard()
    )


async def is_admin(message: Message, state: FSMContext) -> bool:
    """Проверка прав администратора"""
    if not message.from_user:
        return False

    user_id = message.from_user.id  
    if not user_id:
        return False

    async with get_async_session() as session:
        result = await session.execute(select(User.role).where(User.id == user_id))
        current_user_role = result.scalar()
        
        if current_user_role == UserRole.ADMIN:
            return True
        
        await message.answer("Вы не являетесь админом. \nПожалуйста введите пароль!")
        await state.set_state(AdminStates.check_password)
        return False

@admin_router.message(AdminStates.check_password)
async def admin_check_password(message: Message, state: FSMContext):
    """Проверка пароля администратора"""
    try:
        password = message.text
        if password == Config.ADMIN_PASSWORD:
            await message.delete()
            
            await message.answer(
                "Админ-панель управления AI-провайдерами",
                reply_markup=build_admin_keyboard()
            )
            await state.clear()
        else:
            await message.delete()
            await message.answer("Неверный пароль")
            await state.set_state(AdminStates.check_password)
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения с паролем: {e}")
        await message.answer("Произошла ошибка при обработке пароля. Пожалуйста, попробуйте еще раз.")
    return


@admin_router.message(F.text == "Список AI провайдеров")
async def list_ai_creators(message: Message):
    """Показать список AI провайдеров"""
    async with get_async_session() as session:
        result = await session.execute(select(AiCreators))
        creators = list(result.scalars().all())

    if not creators:
        await message.answer("Нет доступных AI провайдеров")
        return

    await message.answer(
        "Выберите AI провайдера:",
        reply_markup=build_ai_creators_keyboard(creators)
    )


@admin_router.message(F.text == "Назад")
async def handle_back(message: Message, state: FSMContext):
    """Обработка кнопки Назад"""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    await admin_panel(message, state)


@admin_router.callback_query(F.data.startswith("select_creator:"))
async def select_creator(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора провайдера"""
    if not callback.data:
        logger.error("Callback data is None")
        await callback.answer("Произошла ошибка: нет данных", show_alert=True)
        return

    try:
        creator_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing callback data: {e}, data: {callback.data}")
        await callback.answer("Неверный формат данных", show_alert=True)
        return

    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        logger.error("Message is inaccessible or None")
        await callback.answer("Произошла ошибка: сообщение недоступно для редактирования", show_alert=True)
        return

    message = callback.message
    if not hasattr(message, 'edit_text'):
        logger.error(f"Message object has no edit_text method: {type(message)}")
        await callback.answer("Произошла ошибка: невозможно обновить сообщение", show_alert=True)
        return

    async with get_async_session() as session:
        creator_result = await session.execute(
            select(AiCreators).where(AiCreators.id == creator_id))
        creator = creator_result.scalars().first()

        if not creator:
            await message.edit_text("Провайдер не найден.")
            await callback.answer()
            return

        await state.update_data(
            ai_creator_id=creator.id,
            ai_creator_name=creator.name,
            ai_creator_url=creator.url
        )

        models_result = await session.execute(
            select(Models).where(Models.ai_creator_id == creator_id))
        models = models_result.scalars().all()

    try:
        if not models:
            await message.edit_text(
                f"У провайдера {creator.name} нет доступных моделей",
                reply_markup=build_back_to_providers_keyboard()
            )
        else:
            await message.edit_text(
                f"Выбран провайдер: {creator.name}\nВыберите модель:",
                reply_markup=build_model_choice_keyboard(models)
            )
    except Exception as e:
        logger.error(f"Error editing message: {e}")

        try:
            text = (f"У провайдера {creator.name} нет доступных моделей" if not models
                else f"Выбран провайдер: {creator.name}\nВыберите модель:")
            markup = (build_back_to_providers_keyboard() if not models
                else build_model_choice_keyboard(models))
            await callback.message.reply(
                text,
                reply_markup=markup
            )
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)

    await callback.answer()

@admin_router.callback_query(F.data.startswith("select_model:"))
async def select_model(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора модели"""
    if not callback.data:
        logger.error("Callback data is None in select_model")
        await callback.answer("Произошла ошибка: нет данных для выбора модели", show_alert=True)
        return

    try:
        model_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing model_id from callback data: {e}, data: {callback.data}")
        await callback.answer("Неверный формат данных для выбора модели", show_alert=True)
        return

    if not callback.message or isinstance(callback.message, InaccessibleMessage):
        logger.error("Message is inaccessible or None in select_model")
        await callback.answer("Произошла ошибка: сообщение недоступно для редактирования", show_alert=True)
        return

    if not hasattr(callback.message, 'edit_text'):
        logger.error(f"Message object has no edit_text method in select_model: {type(callback.message)}")
        await callback.answer("Произошла ошибка: невозможно обновить сообщение", show_alert=True)
        return

    async with get_async_session() as session:
        model_result = await session.execute(
            select(Models).where(Models.id == model_id))
        model: Models = model_result.scalars().first()  # Add type hint

        if not model:
            await callback.message.edit_text("Модель не найдена")
            await callback.answer()
            return

        settings_result = await session.execute(select(AiSettings))
        settings = settings_result.scalars().first()
        if not settings:
            settings = AiSettings()
            session.add(settings)

        await session.execute(
            update(Models).values(selected=False))

        setattr(model, 'selected', True)
        await session.commit()

        creator_result = await session.execute(
            select(AiCreators).where(AiCreators.id == model.ai_creator_id))
        creator = creator_result.scalars().first()

        if not creator:
            logger.error(f"Creator not found for model_id: {model_id} and ai_creator_id: {model.ai_creator_id}")
            await callback.message.edit_text("Ошибка: связанный провайдер не найден. Настройки не применены.")
            await callback.answer()
            return

        try:
            model_temperature = float(settings.temperature) if settings.temperature is not None else 0.0
        except (TypeError, ValueError):
            logger.error("Invalid temperature value in settings")
            model_temperature = 0.0

        await redis_service.save_openai_token(str(creator.token))
        await redis_service.save_selected_url(str(creator.url))
        await redis_service.save_selected_ai_model(str(model.name))
        await redis_service.save_model_temperature(model_temperature)

        await callback.message.edit_text(
            f"Выбрана модель: {model.name}\n"
            f"Провайдер: {creator.name}\n"
            f"Температура: {model_temperature}\n\n"
            "Настройки успешно сохранены!"
        )
    await callback.answer()


@admin_router.message(F.text == "Добавить нового провайдера")
async def add_new_creator_start(message: Message, state: FSMContext):
    """Начало добавления нового провайдера"""
    await state.set_state(AdminStates.creator_name)
    await message.answer("Введите название нового AI провайдера:")


@admin_router.message(AdminStates.creator_name)
async def process_creator_name(message: Message, state: FSMContext):
    """Обработка названия провайдера"""
    await state.update_data(creator_name=message.text)
    await state.set_state(AdminStates.creator_token)
    await message.answer("Введите API токен для этого провайдера:")


@admin_router.message(AdminStates.creator_token)
async def process_creator_token(message: Message, state: FSMContext):
    """Обработка токена провайдера"""
    try:
        await message.delete()
        await state.update_data(creator_token=message.text)
        await state.set_state(AdminStates.creator_url)
        await message.answer("Введите URL API для этого провайдера:")
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения с токеном: {e}")
        await message.answer("Произошла ошибка при обработке токена. Пожалуйста, попробуйте еще раз.")


@admin_router.message(AdminStates.creator_url)
async def process_creator_url(message: Message, state: FSMContext):
    """Обработка URL и сохранение провайдера"""
    data = await state.get_data()

    if not message.text:
        logger.error("Message text is empty")
        await message.answer("Произошла ошибка: URL не указан")
        return

    async with get_async_session() as session:
        new_creator = AiCreators(
            name=data['creator_name'],
            token=data['creator_token'],
            url=message.text
        )
        session.add(new_creator)
        await session.commit()

        await redis_service.save_openai_token(data['creator_token'])
        await redis_service.save_selected_url(message.text)

        await state.update_data(ai_creator_id=new_creator.id)
        await state.set_state(AdminStates.models_url)
        await message.answer(
            f"Провайдер {data['creator_name']} успешно добавлен!\n"
            "Теперь введите URL для загрузки моделей от этого провайдера:"
        )


@admin_router.message(AdminStates.models_url)
async def process_models_url(message: Message, state: FSMContext):
    """Загрузка моделей по URL"""
    data = await state.get_data()
    creator_id = data['ai_creator_id']

    if not message.text:
        logger.error("Message text is empty")
        await message.answer("Произошла ошибка: URL не указан")
        return

    models_url = message.text
    token = await redis_service.load_openai_token()

    if token is None:
        await message.answer("Произошла ошибка, нет токена")
        return

    try:
        success = await load_models(
            models_link=models_url,
            token=str(token),
            creator_id=creator_id,
        )

        if not success:
            await message.answer("Не удалось загрузить модели.")
            return

        async with get_async_session() as session:
            result = await session.execute(
                select(Models).where(Models.ai_creator_id == creator_id))
            models = result.scalars().all()

        if not models:
            await message.answer("Не удалось загрузить модели.")
        else:
            await message.answer(
                "Выберите модель для использования по умолчанию:",
                reply_markup=build_model_choice_keyboard(models)
            )

        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка при загрузке моделей: {str(e)}")
        await state.clear()


@admin_router.message(F.text == "Изменить температуру")
async def change_temperature_start(message: Message, state: FSMContext):
    """Начало изменения температуры"""
    async with get_async_session() as session:
        settings_result = await session.execute(select(AiSettings))
        settings = settings_result.scalars().first()

        if not settings:
            settings = AiSettings(temperature=Config.DEFAULT_TEMPERATURE)
            session.add(settings)
            await session.commit()

        await state.update_data(
            current_temperature=settings.temperature
        )
        await state.set_state(AdminStates.update_temperature)

        await message.answer(
            f"Текущая температура: {settings.temperature}\n\n"
            "Введите новое значение температуры (0.0-2.0):"
        )


@admin_router.message(AdminStates.update_temperature)
async def process_temperature_update(message: Message, state: FSMContext):
    """Обработка изменения температуры"""

    if not message.text:
        logger.error("Message text is empty")
        await message.answer("Произошла ошибка: URL не указан")
        return

    try:
        new_temperature = float(message.text)
        if not 0 <= new_temperature <= 2:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное значение temperature (0.0-2.0)")
        return

    async with get_async_session() as session:
        settings_result = await session.execute(select(AiSettings))
        settings = settings_result.scalars().first()

        if settings:
            settings.temperature = new_temperature
            await session.commit()

            await redis_service.save_model_temperature(new_temperature)

            await message.answer(
                f"Температура изменена на {new_temperature}"
            )
        else:
            await message.answer("Настройки не найдены")

    await state.clear()


@admin_router.message(F.text == "Изменить промпт")
async def change_prompt_start(message: Message, state: FSMContext):
    """Начало изменения системного промпта"""
    async with get_async_session() as session:
        settings_result = await session.execute(select(AiSettings))
        settings = settings_result.scalars().first()

        if not settings:
            settings = AiSettings(prompt=Config.DEFAULT_PROMPT)
            session.add(settings)
            await session.commit()

        current_prompt = settings.prompt or "Промпт не установлен"

        await state.set_state(AdminStates.update_prompt)
        await message.answer(
            f"Текущий системный промпт:\n\n{current_prompt}\n\n"
            "Введите новый системный промпт:",
                parse_mode=None
        )

@admin_router.message(AdminStates.update_prompt)
async def process_prompt(message: Message, state: FSMContext):
    """Обработка системного промпта"""
    if not message.text:
        logger.error("Message text is empty")
        await message.answer("Произошла ошибка: URL не указан")
        return

    new_prompt = message.text

    if len(new_prompt) > 4000:
        await message.answer("Промпт слишком длинный. Максимум 4000 символов.")
        return

    async with get_async_session() as session:
        settings_result = await session.execute(select(AiSettings))
        settings = settings_result.scalars().first()

        if settings:
            setattr(settings, 'prompt', new_prompt)
            await session.commit()

            await redis_service.save_prompt(new_prompt)

            await message.answer(
                "Системный промпт успешно обновлен!\n\n"
                f"Первые 500 символов нового промпта:\n{new_prompt[:500]}...",
                parse_mode=None
            )
        else:
            await message.answer("Ошибка: настройки не найдены")

    await state.clear()


@admin_router.message(F.text == "Список пользователей")
async def list_users(message: Message, state: FSMContext):
    """Показать список пользователей"""
    await state.set_state(AdminStates.users_list)
    await show_users_page(message, state, page=0)

async def show_users_page(message: Message, state: FSMContext, page: int):
    """Показать страницу с пользователями"""
    page_size = 10
    async with get_async_session() as session:
        result = await session.execute(
            select(User)
            .order_by(User.id)
            .offset(page * page_size)
            .limit(page_size)
        )
        users = result.scalars().all()

    if not users:
        await message.answer("Нет пользователей для отображения")
        return

    await message.answer(
        f"Список пользователей (страница {page + 1}):",
        reply_markup=build_users_keyboard(list(users), page, page_size)
    )

def build_users_keyboard(users: list, page: int, page_size: int = 10):
    """Создает клавиатуру для списка пользователей"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for user in users:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{user.id} - {user.username or 'No username'}",
                callback_data=f"user_info:{user.id}"
            )
        ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="Сделать Админом",
                callback_data=f"make_admin:{user.id}"
            ),
            InlineKeyboardButton(
                text="Забанить пользователя",
                callback_data=f"ban_user:{user.id}"
            )
        ])
    
    return keyboard

@admin_router.callback_query(F.data.startswith("ban_user:"))
async def handle_ban_user(callback: CallbackQuery, state: FSMContext):
    """Обработка бана пользователя"""
    try:
        if not callback.data:
            await callback.answer("Не удалось получить сообщение")
            return

        user_id = int(callback.data.split(":")[1])
        
        async with get_async_session() as session:
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(role=UserRole.BANNED)
            )
            await session.commit()
            
            await callback.answer("Пользователь забанен", show_alert=True)
            
            current_state = await state.get_state()
            if current_state == AdminStates.users_list:
                if callback.message and not isinstance(callback.message, InaccessibleMessage):
                    await callback.message.delete()
                    await show_users_page(callback.message, state, page=0)
                else:
                    await callback.answer("Не возможно отобразить список пользователей", show_alert=True)
                
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        await callback.answer("Ошибка при бане пользователя", show_alert=True)

@admin_router.callback_query(F.data.startswith("users_page:"))
async def handle_users_page(callback: CallbackQuery, state: FSMContext):
    """Обработка перехода по страницам"""
    try:
        if not callback.data:
            await callback.answer("Нет данных")
            return
            
        page = int(callback.data.split(":")[1])
        
        if not callback.message:
            await callback.answer("Нет сообщения")
            return
            
        if not isinstance(callback.message, InaccessibleMessage):
            await callback.message.delete()
        if isinstance(callback.message, Message):
            await show_users_page(callback.message, state, page)
        else:
            await callback.answer("Не могу отобразить пользователей")
    except Exception as e:
        logger.error(f"Error handling users page: {e}")
        await callback.answer("Ошибка при переходе по страницам")

@admin_router.callback_query(F.data.startswith("make_admin:"))
async def handle_select_user(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора пользователя"""
    try:
        if not callback.data:
            await callback.answer("Нет никаких данных")
            return
        user_id = int(callback.data.split(":")[1])
        
        async with get_async_session() as session:

            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(role=UserRole.ADMIN)
            )
            await session.commit()
            
            await callback.answer("Пользователь теперь администратор", show_alert=True)
            
            
            current_state = await state.get_state()
            if current_state == AdminStates.users_list:
                if callback.message and not isinstance(callback.message, InaccessibleMessage):
                    await callback.message.delete()
                    await show_users_page(callback.message, state, page=0)
                else:
                    await callback.answer("Не могу отобразить пользователей")
                
    except Exception as e:
        logger.error(f"Error promoting user: {e}")
        await callback.answer("Ошибка при назначении администратора", show_alert=True)

@admin_router.callback_query(F.data == "back_to_admin")
async def handle_back_to_admin(callback: CallbackQuery, state: FSMContext):
    """Возврат в админ-панель"""
    if callback.message and not isinstance(callback.message, InaccessibleMessage):
        await callback.message.delete()
        await admin_panel(callback.message, state)
    else:
        logger.error("Cannot access message in handle_back_to_admin")
        await callback.answer("Не возможно вернуться в панель", show_alert=True)
