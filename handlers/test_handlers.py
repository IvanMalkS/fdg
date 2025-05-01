import asyncio
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from datetime import datetime
from services.gpt import analyze_with_chatgpt
from services.logger import logger
from services.minio_service import MinioService
from services.test_service import prepare_test_data, generate_test_report, get_competencies_for_role, \
    get_available_roles
from services.keyboard import build_roles_keyboard, build_competencies_keyboard, build_start_test_keyboard, \
    build_start_buttons
from handlers.states import TestStates, MainMenuStates
from services.redis_service import RedisService
from db.models import DAMAQuestion, DAMACase
from services.state_service import state_storage
from typing import Dict, Any, Callable, Coroutine

test_router = Router()

redis_service = RedisService()

def handle_errors(error_message: str = "Произошла ошибка. Пожалуйста, попробуйте позже."):
    """Decorator to handle common exceptions in handlers."""
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        async def wrapper(message: types.Message, state: FSMContext, *args, **kwargs):
            try:
                return await func(message, state, *args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в {func.__name__}: {e}")
                await message.answer(f"{error_message} ({e})")
        return wrapper
    return decorator

def _deserialize_question(data: Dict[str, Any]) -> DAMAQuestion:
    """Десериализует данные вопроса в объект DAMAQuestion"""
    question = DAMAQuestion()
    for key, value in data.items():
        setattr(question, key, value)
    return question

def _deserialize_case(data: Dict[str, Any]) -> DAMACase:
    """Десериализует данные кейса в объект DAMACase"""
    case = DAMACase()
    for key, value in data.items():
        setattr(case, key, value)
    return case

@test_router.message(F.text == "Начать тестирование")
@handle_errors("Произошла ошибка при запуске теста.")
async def start_test(message: types.Message, state: FSMContext, **kwargs):
    """Начало тестирования - запрос ФИО"""
    await state.set_state(TestStates.waiting_for_name)
    await message.answer(
        "Добро пожаловать в тестирование компетенций DAMA!\n\n"
        "Для начала, пожалуйста, введите ваше ФИО:",
        reply_markup=types.ReplyKeyboardRemove()
    )


@test_router.message(TestStates.waiting_for_name)
@handle_errors("Произошла ошибка при обработке вашего имени.")
async def process_name(message: types.Message, state: FSMContext, **kwargs):
    """Обработка ФИО и переход к выбору роли"""
    if not message.text.strip():
        await message.answer("Пожалуйста, введите ваше ФИО:")
        return

    user_name = message.text.strip()
    await state.update_data(user_name=user_name)
    await state.set_state(TestStates.waiting_for_role)
    await redis_service.save_user_metadata(message.from_user.id, {'user_name': user_name})

    await message.answer(
        "Выберите вашу роль DAMA из списка ниже:",
        reply_markup=await build_roles_keyboard()
    )

@test_router.message(TestStates.waiting_for_role)
async def process_role(message: types.Message, state: FSMContext):
    """Обработка выбранной роли и переход к выбору компетенции"""
    try:
        selected_role = message.text.strip()
        valid_roles = await get_available_roles()

        if selected_role not in valid_roles:
            await message.answer("Пожалуйста, выберите роль из предложенного списка:")
            return

        await state.update_data(selected_role=selected_role)
        await state.set_state(TestStates.waiting_for_competency)
        await redis_service.save_user_metadata(message.from_user.id, {'selected_role': selected_role})
        await message.answer(
            f"Вы выбрали роль: <b>{selected_role}</b>\n\n"
            "Теперь выберите компетенцию для тестирования:",
            reply_markup=await build_competencies_keyboard(selected_role),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке роли: {e}")
        await message.answer("Произошла ошибка при обработке выбранной роли. Пожалуйста, попробуйте еще раз.")

@test_router.message(TestStates.waiting_for_competency)
async def process_competency(message: types.Message, state: FSMContext):
    """Обработка выбранной компетенции и подготовка теста"""
    try:
        data = await state.get_data()
        selected_comp = message.text.strip()

        valid_comps = await get_competencies_for_role(data['selected_role'])
        if selected_comp not in valid_comps:
            competencies = await get_competencies_for_role(data['selected_role'])
            await message.answer(
                "Пожалуйста, выберите компетенцию из предложенного списка:",
                reply_markup=await build_competencies_keyboard(competencies)
            )
            return

        test_data = await prepare_test_data(data['selected_role'], selected_comp)

        if not test_data['questions']:
            await message.answer("Для выбранной комбинации роли и компетенции нет доступных вопросов.")
            await state.clear()
            return

        serialized_test_data = {
            'questions': [
                {c.name: getattr(q, c.name) for c in q.__table__.columns}
                for q in test_data['questions']
            ],
            'case': {c.name: getattr(test_data['case'], c.name) for c in test_data['case'].__table__.columns} 
            if test_data.get('case') else None
        }

        await state.update_data({
            'selected_comp': selected_comp,
            'total_questions': len(test_data['questions']),
            'has_case': bool(test_data['case']),
            'prepared_data': serialized_test_data
        })

        await redis_service.save_user_metadata(message.from_user.id, {
            'selected_comp': selected_comp,
            'selected_role': data['selected_role'],
            'user_name': data['user_name']
        })

        await state.set_state(TestStates.ready_to_start)

        confirmation_msg = (
            f"<b>Подтвердите выбор:</b>\n\n"
            f"👤 Тестируемый: {data['user_name']}\n"
            f"🏢 Роль: {data['selected_role']}\n"
            f"📚 Компетенция: {selected_comp}\n\n"
            f"Всего вопросов: {len(test_data['questions'])}\n"
            f"Сценарный кейс: {'есть' if test_data['case'] else 'нет'}\n\n"
            "Готовы начать тестирование?"
        )

        await message.answer(
            confirmation_msg,
            reply_markup=build_start_test_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке компетенции: {e}")
        await message.answer(
            "Произошла ошибка при обработке выбранной компетенции. Пожалуйста, попробуйте еще раз."
        )

@test_router.message(TestStates.ready_to_start, F.text == "✅ Начать тестирование")
async def start_testing(message: types.Message, state: FSMContext):
    """Запуск процесса тестирования"""
    try:
        data = await state.get_data()
        test_data = data['prepared_data']

        serialized_data = {
            'questions': test_data['questions'],
            'current_question': 0,
            'answers': [],
            'case': test_data['case'] if test_data.get('case') else None,
            'start_time': datetime.now().isoformat(),
            'awaiting_clarification': False,
            'clarification_count': 0,
            'selected_role': data['selected_role'],
            'selected_comp': data['selected_comp']
        }

        await state.update_data(serialized_data)
        await state.set_state(TestStates.answering_question)
        data = await state.get_data()
        await redis_service.save_user_metadata(message.from_user.id, {
            'user_name': data['user_name'],
            'selected_role': data['selected_role'],
            'selected_comp': data['selected_comp']
        })
        await ask_question(message, state)
    except Exception as e:
        logger.error(f"Ошибка при запуске тестирования: {e}")
        await message.answer("Произошла ошибка при запуске тестирования. Пожалуйста, попробуйте позже.")

async def ask_question(message: types.Message, state: FSMContext):
    """Задание очередного вопроса"""
    data = await state.get_data()
    current_idx = data['current_question']
    questions = data['questions']

    if current_idx >= len(questions):
        await handle_case_presentation(message, state)
        return

    current_question = _deserialize_question(questions[current_idx])

    question_msg = (
        f"<b>Вопрос {current_idx + 1}/{len(questions)}</b>\n\n"
        f"<i>Тип:</i> {current_question.question_type}\n"
        f"<i>Область знаний:</i> {current_question.dama_knowledge_area}\n"
        f"<i>Основные работы:</i> {current_question.dama_main_job}\n\n"
        f"{current_question.question}\n\n"
        "<i>Пожалуйста, дайте развернутый ответ:</i>"
    )

    await message.answer(
        question_msg,
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

@test_router.message(TestStates.answering_question)
async def process_answer(message: types.Message, state: FSMContext, **kwargs):
    """Обработка ответа пользователя на вопрос"""
    data = await state.get_data()
    current_idx = data['current_question']
    questions = data['questions']
    user_id = message.from_user.id

    if data.get('awaiting_clarification', False):
        return await handle_clarification_response(message, state)

    current_question = _deserialize_question(questions[current_idx])

    analysis = await analyze_with_chatgpt(
        question_text=current_question.question,
        correct_answer=current_question.question_answer,
        user_answer=message.text,
        role=data['selected_role'],
        competence=data['selected_comp'],
        user_id=user_id,
        question_id=current_idx
    )


    if analysis.get('needs_clarification', False) and data.get('clarification_count', 0) < 2:
        clarification_prompt = (
            f"Пользователь ответил на вопрос '{current_question.question}' следующим образом:\n\n"
            f"{message.text}\n\n"
            f"Уточняющий вопрос: {analysis['clarification_question']}\n\n"
            "Пожалуйста, дайте более развернутый ответ, учитывая предыдущее сообщение."
        )

        await state.update_data({
            'awaiting_clarification': True,
            'clarification_question': clarification_prompt,
            'previous_feedback': analysis,
            'previous_answer': message.text,
            'clarification_count': data.get('clarification_count', 0) + 1
        })

        await message.answer(
            analysis['clarification_question'],
            parse_mode="HTML"
        )
        return

    answer_data = {
        'question': current_question.question,
        'user_answer': message.text,
        'correct_answer': current_question.question_answer,
        'score': analysis['score'],
        'feedback': {
            'strengths': analysis['strengths'],
            'weaknesses': analysis['weaknesses'],
            'recommendations': analysis['recommendations']
        },
        'knowledge_area': current_question.dama_knowledge_area,
        'main_job': current_question.dama_main_job,
        'question_type': current_question.question_type,
        'timestamp': datetime.now().isoformat(),
        'clarification_used': data.get('clarification_count', 0) > 0
    }

    await redis_service.save_answers_to_redis(
        user_id=user_id,
        question_id=current_idx,
        data=answer_data
    )

    new_data = {
        'current_question': current_idx + 1,
        'answers': data['answers'] + [answer_data],
        'awaiting_clarification': False,
        'clarification_count': 0
    }
    await state.update_data(new_data)

    feedback_msg = format_feedback(analysis)
    await message.answer(feedback_msg, parse_mode="HTML")

    await asyncio.sleep(2)

    if new_data['current_question'] >= len(questions):
        await handle_case_presentation(message, state)
    else:
        await ask_question(message, state)

async def handle_clarification_response(message: types.Message, state: FSMContext):
    """Обработка ответа на уточняющий вопрос"""
    data = await state.get_data()
    current_idx = data['current_question']
    questions = data['questions']
    user_id = message.from_user.id

    try:
        current_question = _deserialize_question(questions[current_idx])
        context = (
            f"Исходный вопрос: {current_question.question}\n"
            f"Первый ответ пользователя: {data['previous_answer']}\n"
            f"Уточняющий ответ: {message.text}"
        )

        analysis = await analyze_with_chatgpt(
            question_text=data['clarification_question'],
            correct_answer=current_question.question_answer,
            user_answer=context,
            role=data['selected_role'],
            competence=data['selected_comp'],
            user_id=user_id,
            question_id=current_idx
        )

        prev_answer = data['answers'][-1] if data['answers'] else None
        if prev_answer:
            combined_answer = f"{prev_answer['user_answer']}\n\nДополнение: {message.text}"
            prev_answer['user_answer'] = combined_answer
            prev_answer['score'] = (prev_answer.get('score', 0) + analysis['score']) / 2
            prev_answer['feedback']['strengths'].extend(analysis['strengths'])
            prev_answer['feedback']['weaknesses'].extend(analysis['weaknesses'])
            prev_answer['feedback']['recommendations'].extend(analysis['recommendations'])
            prev_answer['clarification_response'] = message.text
            prev_answer['is_clarified'] = True

            await redis_service.save_answers_to_redis(
                user_id=user_id,
                question_id=current_idx,
                data=prev_answer
            )

        new_data = {
            'awaiting_clarification': False,
            'clarification_count': 0,
            'previous_feedback': None,
            'previous_answer': None,
            'current_question': current_idx + 1,
            'answers': data['answers'] + [prev_answer] if prev_answer else data['answers']
        }
        await state.update_data(new_data)

        feedback_msg = (
            f"<b>Ваш уточненный ответ оценен на {analysis['score']:.1f}/5.0</b>\n\n"
            f"<i>Исходный ответ:</i>\n{data['previous_answer']}\n\n"
            f"<i>Уточнение:</i>\n{message.text}\n\n"
            f"<i>Итоговая оценка:</i>\n{format_feedback(analysis)}"
        )

        await message.answer(
            feedback_msg,
            parse_mode="HTML"
        )

        await asyncio.sleep(2)

        if new_data['current_question'] >= len(questions):
            await handle_case_presentation(message, state)
        else:
            await ask_question(message, state)

    except Exception as e:
        logger.error(f"Ошибка при обработке уточнения: {e}")
        await message.answer("Произошла ошибка при обработке вашего уточнения. Продолжим со следующим вопросом.")
        await state.update_data({
            'awaiting_clarification': False,
            'clarification_count': 0,
            'current_question': current_idx + 1
        })
        await ask_question(message, state)

async def handle_case_presentation(message: types.Message, state: FSMContext):
    """Представление сценарного кейса (если есть)"""
    data = await state.get_data()

    if not data.get('case'):
        await generate_report(message, message.from_user.id)
        return

    case = _deserialize_case(data['case'])
    case_msg = (
        "<b>Сценарный кейс</b>\n\n"
        f"<i>Ситуация:</i> {case.situation}\n\n"
        f"<i>Задача:</i> {case.case_task}\n\n"
        "<i>Пожалуйста, предложите ваше решение:</i>"
    )

    await state.set_state(TestStates.answering_case)
    await message.answer(case_msg, parse_mode="HTML")

@test_router.message(TestStates.answering_case)
async def process_case_answer(message: types.Message, state: FSMContext):
    """Обработка ответа на сценарный кейс"""
    data = await state.get_data()
    user_id = message.from_user.id
    current_idx = data['current_question'] + 1

    try:
        case = _deserialize_case(data['case'])

        analysis = await analyze_with_chatgpt(
            question_text=f"{case.situation}\n\n{case.case_task}",
            correct_answer=case.case_answer,
            user_answer=message.text,
            role=data['selected_role'],
            competence=data['selected_comp'],
            user_id = user_id,
            question_id = current_idx
        )


        case_data = {
            'question': f"{case.situation}\n\n{case.case_task}",
            'user_answer': message.text,
            'correct_answer': case.case_answer,
            'score': analysis['score'],
            'feedback': {
                'strengths': analysis['strengths'],
                'weaknesses': analysis['weaknesses'],
                'recommendations': analysis['recommendations']
            },
            'knowledge_area': case.dama_knowledge_area,
            'main_job': case.dama_main_job,
            'question_type': "Сценарный кейс",
            'timestamp': datetime.now().isoformat()
        }

        await redis_service.save_answers_to_redis(
            user_id=user_id,
            question_id=len(data['questions']),
            data=case_data
        )

        feedback_msg = format_feedback(analysis, is_case=True)
        await message.answer(feedback_msg, parse_mode="HTML")

        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Ошибка при обработке кейса: {e}")
        await message.answer("Произошла ошибка при оценке кейса. Переходим к отчету...")

    await generate_report(message, user_id, state)

async def generate_report(message: types.Message, user_id: int, state: FSMContext):
    """Генерация отчета и загрузка в MinIO"""
    minio_service = MinioService()

    try:
        report = await generate_test_report(user_id)

        if not report:
            raise ValueError("Не удалось сгенерировать отчет")

        success, filename = await minio_service.upload_report(
            user_id=user_id,
            file_data=report['excel_file']
        )

        if not success:
            raise ValueError("Не удалось загрузить отчет в хранилище")

        download_url = await minio_service.get_report_url(filename)

        if not download_url:
            raise ValueError("Не удалось получить ссылку для скачивания")

        result_msg = (
            "<b>Тестирование завершено!</b>\n\n"
            f"<b>Средний балл:</b> {report['avg_score']:.2f}\n"
            f"<b>Уровень эксперта:</b> {'достигнут' if report['is_expert'] else 'не достигнут'}\n\n"
            f"Скачать полный отчет:\n"
            f"{download_url}\n\n"
            "Выберите действие:"
        )

        await message.answer(
            result_msg,
            reply_markup=build_start_buttons(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Ошибка при генерации отчета: {e}")
        user_meta = await redis_service.get_user_metadata(user_id)
        report = await generate_test_report(user_id)
        # Fallback - отправка файла напрямую, если MinIO не работает
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fallback_filename = f"DAMA_Report_{user_meta.get('user_name')}_{timestamp}.xlsx"
        excel_file = types.BufferedInputFile(
            report['excel_file'].getvalue(),
            filename=fallback_filename
        )


        await message.answer_document(
            excel_file,
            caption="Ваш отчет об оценке компетенций DAMA"
        )

        await message.answer(
            "Произошла ошибка при загрузке в облачное хранилище. Отчет отправлен напрямую.",
            reply_markup=build_start_buttons()
        )

    finally:
        await redis_service.clear_user_answers(user_id)
        await redis_service.clear_user_metadata(user_id)
        await state_storage.clear_state(user_id)
        await state.set_state(MainMenuStates.main_menu)

def format_feedback(analysis: dict, is_case: bool = False) -> str:
    """Форматирование обратной связи для пользователя"""
    question_type = "кейса" if is_case else "вопроса"
    strengths = "\n".join([f"• {s}" for s in analysis.get('strengths', [])])
    recommendations = "\n".join([f"• {r}" for r in analysis.get('recommendations', [])])

    return (
        f"<b>Ваш ответ на {question_type} оценен на {analysis['score']:.1f}/5.0</b>\n\n"
        f"<i>Сильные стороны:</i>\n{strengths}\n\n"
        f"<i>Рекомендации:</i>\n{recommendations}"
    )