# bots_factory/app/bot/states.py

from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    confirming_booking = State()