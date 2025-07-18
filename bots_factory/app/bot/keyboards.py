from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar
from aiogram.filters.callback_data import CallbackData
from typing import List
from .api_client import Service, Master

# --- Фабрики колбэков для обработки нажатий ---
class ServiceCallback(CallbackData, prefix="srv"):
    service_id: int
    service_name: str

class MasterCallback(CallbackData, prefix="mstr"):
    master_id: int
    master_name: str

class TimeSlotCallback(CallbackData, prefix="ts"):
    time: str
    
class ConfirmationCallback(CallbackData, prefix="confirm"):
    action: str # 'yes' or 'no'

# --- Клавиатуры ---
main_menu_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="✍️ Записаться на услугу")]
], resize_keyboard=True, input_field_placeholder="Выберите действие из меню:")

def get_services_kb(services: List[Service]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in services:
        builder.button(text=s.name, callback_data=ServiceCallback(service_id=s.id, service_name=s.name))
    builder.adjust(1) # По одной кнопке в ряд
    return builder.as_markup()

def get_masters_kb(masters: List[Master]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in masters:
        builder.button(text=m.name, callback_data=MasterCallback(master_id=m.id, master_name=m.name))
    builder.adjust(1)
    return builder.as_markup()

def get_time_slots_kb(slots: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for time in slots:
        builder.button(text=time, callback_data=TimeSlotCallback(time=time))
    builder.adjust(4) # По 4 кнопки в ряд
    return builder.as_markup()

confirm_booking_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=ConfirmationCallback(action="yes").pack()),
        InlineKeyboardButton(text="❌ Отмена", callback_data=ConfirmationCallback(action="no").pack())
    ]
])

async def get_calendar_kb() -> InlineKeyboardMarkup:
    return await SimpleCalendar().start_calendar()