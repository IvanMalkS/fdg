from aiogram.fsm.state import State, StatesGroup

class MainMenuStates(StatesGroup):
    main_menu = State()

class TestStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_role = State()
    waiting_for_competency = State()
    ready_to_start = State()
    answering_question = State()
    answering_case = State()

class AdminStates(StatesGroup):
    check_password = State()
    creator_name = State()
    creator_token = State()
    creator_url = State()
    models_url = State()
    model_name = State()
    update_temperature = State()
    update_prompt = State()
    users_list = State()