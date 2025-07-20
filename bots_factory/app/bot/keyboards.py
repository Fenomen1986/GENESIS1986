# bots_factory/app/bot/keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import calendar
from datetime import datetime, timedelta

def create_services_keyboard(services: list) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора услуги."""
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.button(text=f"{service['name']} ({service['price']} руб.)", callback_data=f"service_{service['id']}")
    builder.adjust(1)
    return builder.as_markup()

def create_masters_keyboard(masters: list) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора мастера."""
    builder = InlineKeyboardBuilder()
    for master in masters:
        builder.button(text=master['name'], callback_data=f"master_{master['id']}")
    builder.button(text="⬅️ Назад к выбору услуг", callback_data="back_to_services")
    builder.adjust(1)
    return builder.as_markup()

def create_calendar_keyboard(year: int = None, month: int = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру-календарь для выбора даты."""
    now = datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month
    
    builder = InlineKeyboardBuilder()
    # Название месяца и год
    builder.button(text=calendar.month_name[month] + " " + str(year), callback_data="ignore")
    # Дни недели
    for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        builder.button(text=day, callback_data="ignore")

    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        for day in week:
            if day == 0:
                builder.button(text=" ", callback_data="ignore")
            else:
                # Проверяем, что дата не в прошлом
                current_date = datetime(year, month, day)
                if current_date.date() < now.date():
                     builder.button(text=str(day), callback_data="ignore_past_date")
                else:
                     builder.button(text=str(day), callback_data=f"date_{year}-{month:02d}-{day:02d}")
    
    # Кнопки навигации по месяцам
    prev_month_date = (datetime(year, month, 1) - timedelta(days=1))
    # Не даем уйти в прошлый месяц, если он уже прошел
    if prev_month_date.year < now.year or (prev_month_date.year == now.year and prev_month_date.month < now.month):
        builder.button(text=" ", callback_data="ignore")
    else:
        builder.button(text="<", callback_data=f"prev-month_{year}-{month}")

    builder.button(text=" ", callback_data="ignore")
    
    next_month_date = (datetime(year, month, 28) + timedelta(days=4))
    builder.button(text=">", callback_data=f"next-month_{year}-{month}")

    builder.button(text="⬅️ Назад к выбору мастера", callback_data="back_to_masters")

    builder.adjust(1, 7, 7, 7, 7, 7, 7, 3, 1) # Гибкая настройка рядов
    return builder.as_markup()

def create_time_slots_keyboard(slots: list) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора временного слота."""
    builder = InlineKeyboardBuilder()
    if not slots:
        builder.button(text="Нет свободных слотов на эту дату", callback_data="no_slots")
    else:
        for slot in slots:
            builder.button(text=slot, callback_data=f"time_{slot}")
    
    builder.button(text="⬅️ Назад к выбору даты", callback_data="back_to_date")
    builder.adjust(4, 1)
    return builder.as_markup()

def create_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения записи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data="confirm_booking")
    builder.button(text="⬅️ Назад к выбору времени", callback_data="back_to_time")
    builder.button(text="❌ Отменить", callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()