# bots_factory/app/bot/handlers.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from datetime import datetime, timedelta

# Исправленные абсолютные импорты
from app.bot import keyboards as kb
from app.bot import api_client
from app.bot.states import BookingStates

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, tenant_id: str):
    await state.clear()
    services = await api_client.get_services(tenant_id)
    if not services:
        await message.answer("Здравствуйте! К сожалению, сейчас нет доступных услуг. Попробуйте позже.")
        return
    await state.update_data(services=services)
    await message.answer("Здравствуйте! Выберите услугу:", reply_markup=kb.create_services_keyboard(services))
    await state.set_state(BookingStates.choosing_service)

# Обработка выбора услуги
@router.callback_query(BookingStates.choosing_service, F.data.startswith("service_"))
async def process_service_choice(callback: CallbackQuery, state: FSMContext, tenant_id: str):
    service_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    services = data.get('services', [])
    selected_service = next((s for s in services if s['id'] == service_id), None)
    if not selected_service:
        await callback.answer("Ошибка! Услуга не найдена.", show_alert=True)
        return

    await state.update_data(service_id=service_id, service_name=selected_service['name'])
    masters = await api_client.get_masters(tenant_id)
    if not masters:
        await callback.message.edit_text("К сожалению, сейчас нет свободных мастеров.")
        return
        
    await state.update_data(masters=masters)
    await callback.message.edit_text("Отлично! Теперь выберите мастера:", reply_markup=kb.create_masters_keyboard(masters))
    await state.set_state(BookingStates.choosing_master)
    await callback.answer()

# Обработка выбора мастера
@router.callback_query(BookingStates.choosing_master, F.data.startswith("master_"))
async def process_master_choice(callback: CallbackQuery, state: FSMContext, tenant_id: str):
    master_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    masters = data.get('masters', [])
    selected_master = next((m for m in masters if m['id'] == master_id), None)
    if not selected_master:
        await callback.answer("Ошибка! Мастер не найден.", show_alert=True)
        return

    await state.update_data(master_id=master_id, master_name=selected_master['name'])
    await callback.message.edit_text("Выберите дату:", reply_markup=kb.create_calendar_keyboard())
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()

# Навигация по календарю
@router.callback_query(BookingStates.choosing_date, F.data.startswith(("prev-month_", "next-month_")))
async def process_calendar_navigation(callback: CallbackQuery, state: FSMContext):
    action, date_str = callback.data.split("_")
    year, month = map(int, date_str.split("-"))
    
    current_date = datetime(year, month, 1)
    if action == "prev-month_":
        new_date = current_date - timedelta(days=1)
    else:
        new_date = current_date + timedelta(days=32)

    await callback.message.edit_reply_markup(reply_markup=kb.create_calendar_keyboard(new_date.year, new_date.month))
    await callback.answer()

# Обработка выбора даты
@router.callback_query(BookingStates.choosing_date, F.data.startswith("date_"))
async def process_date_choice(callback: CallbackQuery, state: FSMContext, tenant_id: str):
    selected_date = callback.data.split("_")[1]
    await state.update_data(selected_date=selected_date)
    data = await state.get_data()
    master_id = data.get('master_id')
    slots = await api_client.get_available_slots(tenant_id, master_id, selected_date)
    
    await callback.message.edit_text(f"Выбрана дата: {selected_date}\nТеперь выберите время:", 
                                     reply_markup=kb.create_time_slots_keyboard(slots))
    await state.set_state(BookingStates.choosing_time)
    await callback.answer()

# Обработка выбора времени
@router.callback_query(BookingStates.choosing_time, F.data.startswith("time_"))
async def process_time_choice(callback: CallbackQuery, state: FSMContext):
    selected_time = callback.data.split("_")[1]
    await state.update_data(selected_time=selected_time)
    data = await state.get_data()
    summary = (f"Пожалуйста, подтвердите вашу запись:\n\n"
               f"Услуга: {data['service_name']}\n"
               f"Мастер: {data['master_name']}\n"
               f"Дата: {data['selected_date']}\n"
               f"Время: {selected_time}")
    
    await callback.message.edit_text(summary, reply_markup=kb.create_confirmation_keyboard())
    await state.set_state(BookingStates.confirming_booking)
    await callback.answer()

# Подтверждение записи
@router.callback_query(BookingStates.confirming_booking, F.data == "confirm_booking")
async def process_booking_confirmation(callback: CallbackQuery, state: FSMContext, tenant_id: str):
    data = await state.get_data()
    user = callback.from_user
    start_time_str = f"{data['selected_date']}T{data['selected_time']}"
    
    booking_payload = {
        "start_time": start_time_str,
        "service_id": data['service_id'],
        "master_id": data['master_id'],
        "client_telegram_id": user.id,
        "client_first_name": user.first_name,
        "client_last_name": user.last_name,
        "client_username": user.username,
    }
    
    success = await api_client.create_booking(tenant_id, booking_payload)
    if success:
        await callback.message.edit_text("✅ Отлично! Вы успешно записаны. Ждем вас!")
    else:
        await callback.message.edit_text("❌ Произошла ошибка при создании записи. Попробуйте снова.")
    await state.clear()
    await callback.answer()

# Кнопки "Назад" и отмены
@router.callback_query(F.data.startswith("back_to_"))
async def process_back_button(callback: CallbackQuery, state: FSMContext, tenant_id: str):
    action = callback.data.split("_")[-1]
    if action == "services":
        await cmd_start(callback.message, state, tenant_id)
    elif action == "masters":
        data = await state.get_data()
        await callback.message.edit_text("Выберите услугу:", reply_markup=kb.create_services_keyboard(data.get('services', [])))
        await state.set_state(BookingStates.choosing_service)
    elif action == "date":
        data = await state.get_data()
        await callback.message.edit_text("Выберите мастера:", reply_markup=kb.create_masters_keyboard(data.get('masters', [])))
        await state.set_state(BookingStates.choosing_master)
    elif action == "time":
        await callback.message.edit_text("Выберите дату:", reply_markup=kb.create_calendar_keyboard())
        await state.set_state(BookingStates.choosing_date)
    await callback.answer()

@router.callback_query(F.data == "cancel_booking")
async def process_cancel_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запись отменена.")
    await callback.answer()

@router.message()
async def any_message_handler(message: Message):
    await message.reply("Пожалуйста, используйте кнопки для навигации или введите /start, чтобы начать заново.")
