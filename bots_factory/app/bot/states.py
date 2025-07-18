from aiogram.fsm.state import StatesGroup, State

class Booking(StatesGroup):
    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    confirmation = State()