from aiogram.fsm.state import State, StatesGroup


class BookingState(StatesGroup):
    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()
