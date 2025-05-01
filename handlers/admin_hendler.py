from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from sqlalchemy import update
from db.models import AiCreators, Models, AiSettings
from db.database import get_async_session, load_models
from handlers.states import AdminStates
from services.keyboard import build_ai_creators_keyboard, build_admin_keyboard, build_model_choice_keyboard, \
    build_back_to_providers_keyboard
from services.redis_service import RedisService

admin_router = Router()
redis_service = RedisService()


@admin_router.message(F.text == "Админ")
async def admin_panel(message: Message):
    """Административная панель"""
    if not await is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора")
        return

    await message.answer(
        "Админ-панель управления AI-провайдерами",
        reply_markup=build_admin_keyboard()
    )


async def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    # TODO: реализовать проверку прав
    return True


@admin_router.message(F.text == "Список AI провайдеров")
async def list_ai_creators(message: Message):
    """Показать список AI провайдеров"""
    async with get_async_session() as session:
        result = await session.execute(select(AiCreators))
        creators = result.scalars().all()

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
    await admin_panel(message)


@admin_router.callback_query(F.data.startswith("select_creator:"))
async def select_creator(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора провайдера"""
    creator_id = int(callback.data.split(":")[1])

    async with get_async_session() as session:
        creator_result = await session.execute(
            select(AiCreators).where(AiCreators.id == creator_id))
        creator = creator_result.scalars().first()

        if not creator:
            await callback.message.edit_text("Провайдер не найден.")
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

    if not models:
        await callback.message.edit_text(
            f"У провайдера {creator.name} нет доступных моделей",
            reply_markup=build_back_to_providers_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"Выбран провайдер: {creator.name}\nВыберите модель:",
            reply_markup=build_model_choice_keyboard(models)
        )

    await callback.answer()


@admin_router.callback_query(F.data.startswith("select_model:"))
async def select_model(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора модели"""
    model_id = int(callback.data.split(":")[1])

    async with get_async_session() as session:
        model_result = await session.execute(
            select(Models).where(Models.id == model_id))
        model = model_result.scalars().first()

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

        model.selected = True
        await session.commit()

        creator_result = await session.execute(
            select(AiCreators).where(AiCreators.id == model.ai_creator_id))
        creator = creator_result.scalars().first()

        await redis_service.save_openai_token(creator.token)
        await redis_service.save_selected_url(creator.url)
        await redis_service.save_selected_ai_model(model.name)
        await redis_service.save_model_temperature(settings.temperature)

        await callback.message.edit_text(
            f"Выбрана модель: {model.name}\n"
            f"Провайдер: {creator.name}\n"
            f"Температура: {settings.temperature}\n\n"
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
    await state.update_data(creator_token=message.text)
    await state.set_state(AdminStates.creator_url)
    await message.answer("Введите URL API для этого провайдера:")


@admin_router.message(AdminStates.creator_url)
async def process_creator_url(message: Message, state: FSMContext):
    """Обработка URL и сохранение провайдера"""
    data = await state.get_data()

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
            settings = AiSettings(temperature=0.7)
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