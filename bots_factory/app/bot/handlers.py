from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
import datetime

# ИЗМЕНЕНИЯ: Абсолютные импорты
from app.bot.states import Booking
from app.bot.keyboards import (
    main_menu_kb, get_services_kb, get_masters_kb, 
    get_time_slots_kb, confirm_booking_kb,
    ServiceCallback, MasterCallback, TimeSlotCallback, ConfirmationCallback
)
from app.bot.api_client import ApiClient

router = Router()
API_URL = "http://api:8000" # Укажем и здесь

@router.message(CommandStart())
async def command_start_handler(message: Message):
    business_name = message.bot.business_name
    await message.answer(f"👋 Добро пожаловать в {business_name}!", reply_markup=main_menu_kb)

# ... (остальной код handlers.py без изменений)

from .states import Booking
from .keyboards import (
    main_menu_kb, get_services_kb, get_masters_kb, 
    get_time_slots_kb, confirm_booking_kb, get_calendar_kb,
    ServiceCallback, MasterCallback, TimeSlotCallback, ConfirmationCallback
)
from .api_client import ApiClient
import datetime

router = Router()

# --- Общие команды ---
@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    await state.clear()
    business_name = message.bot.business_name
    await message.answer(f"👋 Добро пожаловать в <b>{business_name}</b>!", reply_markup=main_menu_kb)

@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=main_menu_kb)

# --- Логика записи ---
@router.message(F.text == "✍️ Записаться на услугу")
async def start_booking(message: Message, state: FSMContext):
    api_client = ApiClient(tenant_id=message.bot.tenant_id)
    services = await api_client.get_services()
    if not services:
        await message.answer("К сожалению, сейчас нет доступных услуг для записи.")
        return
    
    await state.set_state(Booking.choosing_service)
    await message.answer("Выберите услугу:", reply_markup=get_services_kb(services))

@router.callback_query(Booking.choosing_service, ServiceCallback.filter())
async def process_service_choice(callback: CallbackQuery, callback_data: ServiceCallback, state: FSMContext):
    await state.update_data(service_id=callback_data.service_id, service_name=callback_data.service_name)
    await callback.message.edit_text(f"Услуга: <b>{callback_data.service_name}</b>")
    
    api_client = ApiClient(tenant_id=callback.message.bot.tenant_id)
    masters = await api_client.get_masters()
    if not masters:
        await callback.message.answer("К сожалению, сейчас нет доступных мастеров. Попробуйте позже.")
        await state.clear()
        return

    await state.set_state(Booking.choosing_master)
    await callback.message.answer("Теперь выберите мастера:", reply_markup=get_masters_kb(masters))
    await callback.answer()

@router.callback_query(Booking.choosing_master, MasterCallback.filter())
async def process_master_choice(callback: CallbackQuery, callback_data: MasterCallback, state: FSMContext):
    await state.update_data(master_id=callback_data.master_id, master_name=callback_data.master_name)
    await callback.message.edit_text(f"Мастер: <b>{callback_data.master_name}</b>")

    await state.set_state(Booking.choosing_date)
    await callback.message.answer("Выберите дату:", reply_markup=await get_calendar_kb())
    await callback.answer()

@router.callback_query(Booking.choosing_date, SimpleCalendarCallback.filter())
async def process_date_choice(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    date = callback_data.get_date()
    if date < datetime.date.today():
        await callback.answer("Нельзя выбрать прошедшую дату!", show_alert=True)
        return
        
    date_str = date.strftime("%Y-%m-%d")
    await state.update_data(date=date_str)
    await callback.message.edit_text(f"Выбранная дата: <b>{date.strftime('%d.%m.%Y')}</b>")

    user_data = await state.get_data()
    api_client = ApiClient(tenant_id=callback.message.bot.tenant_id)
    slots = await api_client.get_available_slots(user_data['master_id'], date_str)
    
    if not slots:
        await callback.message.answer("На эту дату свободных слотов нет. Пожалуйста, выберите другую.", reply_markup=await get_calendar_kb())
        return

    await state.set_state(Booking.choosing_time)
    await callback.message.answer("Выберите удобное время:", reply_markup=get_time_slots_kb(slots))
    await callback.answer()

@router.callback_query(Booking.choosing_time, TimeSlotCallback.filter())
async def process_time_choice(callback: CallbackQuery, callback_data: TimeSlotCallback, state: FSMContext):
    await state.update_data(time=callback_data.time)
    user_data = await state.get_data()
    
    date_formatted = datetime.datetime.strptime(user_data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
    
    text = (
        "Пожалуйста, проверьте и подтвердите вашу запись:\n\n"
        f"<b>Услуга:</b> {user_data['service_name']}\n"
        f"<b>Мастер:</b> {user_data['master_name']}\n"
        f"<b>Дата:</b> {date_formatted}\n"
        f"<b>Время:</b> {user_data['time']}"
    )
    
    await state.set_state(Booking.confirmation)
    await callback.message.edit_text(text, reply_markup=confirm_booking_kb)
    await callback.answer()

@router.callback_query(Booking.confirmation, ConfirmationCallback.filter(F.action == "yes"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    api_client = ApiClient(tenant_id=callback.message.bot.tenant_id)
    
    booking_data = {
        "service_id": user_data['service_id'],
        "master_id": user_data['master_id'],
        "client_telegram_id": callback.from_user.id,
        "client_first_name": callback.from_user.first_name,
        "client_last_name": callback.from_user.last_name,
        "client_username": callback.from_user.username,
        "start_time": f"{user_data['date']}T{user_data['time']}:00"
    }

    success = await api_client.create_booking(booking_data)
    if success:
        await callback.message.edit_text("✅ <b>Отлично! Вы успешно записаны.</b>")
    else:
        await callback.message.edit_text("❌ Произошла ошибка при создании записи. Попробуйте позже.")
        
    await state.clear()
    await callback.answer()

@router.callback_query(Booking.confirmation, ConfirmationCallback.filter(F.action == "no"))
async def process_cancellation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запись отменена.", reply_markup=main_menu_kb)
    await callback.answer()