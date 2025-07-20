# bots_factory/app/web/crud.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from fastapi import HTTPException, status
import datetime
from typing import List, Optional

from . import models, schemas
from .security import get_password_hash

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(func.lower(models.User.username) == func.lower(username)).first()

def get_services(db: Session, tenant_id: str):
    return db.query(models.Service).filter(models.Service.tenant_id == tenant_id).order_by(models.Service.name).all()

def create_service(db: Session, service: schemas.ServiceCreate, tenant_id: str):
    db_service = models.Service(**service.model_dump(), tenant_id=tenant_id, is_active=True)
    db.add(db_service); db.commit(); db.refresh(db_service)
    return db_service

def update_service(db: Session, service_id: int, service_data: schemas.ServiceCreate, tenant_id: str):
    db_service = db.query(models.Service).filter(models.Service.id == service_id, models.Service.tenant_id == tenant_id).first()
    if not db_service: raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    for key, value in service_data.model_dump().items():
        setattr(db_service, key, value)
    db.commit(); db.refresh(db_service)
    return db_service

def delete_service(db: Session, service_id: int, tenant_id: str):
    db_service = db.query(models.Service).filter(models.Service.id == service_id, models.Service.tenant_id == tenant_id).first()
    if not db_service: raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    db.delete(db_service); db.commit()

def get_master(db: Session, master_id: int, tenant_id: str):
    return db.query(models.Master).options(joinedload(models.Master.schedules)).filter(models.Master.id == master_id, models.Master.tenant_id == tenant_id).first()

def get_masters(db: Session, tenant_id: str):
    return db.query(models.Master).options(joinedload(models.Master.schedules)).filter(models.Master.tenant_id == tenant_id).order_by(models.Master.name).all()

def create_master(db: Session, master: schemas.MasterCreate, tenant_id: str):
    db_master = models.Master(**master.model_dump(), tenant_id=tenant_id)
    db.add(db_master)
    db.commit()
    db.refresh(db_master)
    default_schedule = []
    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    for day in models.DayOfWeekEnum:
        is_day_off = day.value not in days_of_week
        schedule_entry = models.WorkSchedule(master_id=db_master.id, day_of_week=day, start_time=datetime.time(9, 0), end_time=datetime.time(18, 0), is_day_off=is_day_off)
        default_schedule.append(schedule_entry)
    db.add_all(default_schedule)
    db.commit()
    db.refresh(db_master)
    return db_master

def update_master(db: Session, master_id: int, master_data: schemas.MasterUpdate, tenant_id: str):
    db_master = get_master(db, master_id=master_id, tenant_id=tenant_id)
    if not db_master: raise HTTPException(status.HTTP_404_NOT_FOUND, "Master not found")
    for key, value in master_data.model_dump(exclude_unset=True).items():
        setattr(db_master, key, value)
    db.commit(); db.refresh(db_master)
    return db_master

def delete_master(db: Session, master_id: int, tenant_id: str):
    db_master = get_master(db, master_id=master_id, tenant_id=tenant_id)
    if not db_master: raise HTTPException(status.HTTP_404_NOT_FOUND, "Master not found")
    db.delete(db_master); db.commit()

def update_work_schedule(db: Session, master_id: int, schedules: List[schemas.WorkScheduleCreate], tenant_id: str):
    db_master = get_master(db, master_id, tenant_id)
    if not db_master: raise HTTPException(status.HTTP_404_NOT_FOUND, "Master not found")
    db.query(models.WorkSchedule).filter(models.WorkSchedule.master_id == master_id).delete()
    db.flush()
    for schedule_data in schedules:
        db.add(models.WorkSchedule(master_id=master_id, **schedule_data.model_dump()))
    db.commit(); db.refresh(db_master)
    return db_master.schedules

def get_clients(db: Session, tenant_id: str, search: Optional[str] = None, page: int = 1, page_size: int = 50):
    query = db.query(models.Client).filter(models.Client.tenant_id == tenant_id)
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(or_(func.lower(models.Client.first_name).like(search_term), func.lower(models.Client.last_name).like(search_term), models.Client.phone_number.like(search_term)))
    total_count = query.count()
    clients = query.order_by(models.Client.first_name).offset((page - 1) * page_size).limit(page_size).all()
    return schemas.PaginatedClients(total_count=total_count, clients=clients)

def get_client_details(db: Session, client_id: int, tenant_id: str):
    return db.query(models.Client).options(joinedload(models.Client.bookings).options(joinedload(models.Booking.service), joinedload(models.Booking.master))).filter(models.Client.id == client_id, models.Client.tenant_id == tenant_id).first()

def update_client(db: Session, client_id: int, client_data: schemas.ClientUpdate, tenant_id: str):
    db_client = db.query(models.Client).filter(models.Client.id == client_id, models.Client.tenant_id == tenant_id).first()
    if not db_client: raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")
    for key, value in client_data.model_dump(exclude_unset=True).items():
        setattr(db_client, key, value)
    db.commit(); db.refresh(db_client)
    return db_client

def create_client(db: Session, client_data: schemas.ClientCreate, tenant_id: str) -> models.Client:
    temp_telegram_id = f"manual_{datetime.datetime.utcnow().timestamp()}"
    db_client = models.Client(**client_data.model_dump(), tenant_id=tenant_id, telegram_id=temp_telegram_id)
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

def get_bookings(db: Session, tenant_id: str, start_date: datetime.datetime, end_date: datetime.datetime):
    return db.query(models.Booking).options(joinedload(models.Booking.service), joinedload(models.Booking.master), joinedload(models.Booking.client)).filter(models.Booking.tenant_id == tenant_id, models.Booking.start_time < end_date, models.Booking.end_time > start_date).all()

def get_booking(db: Session, booking_id: int, tenant_id: str):
    return db.query(models.Booking).options(joinedload(models.Booking.service), joinedload(models.Booking.master), joinedload(models.Booking.client)).filter(models.Booking.id == booking_id, models.Booking.tenant_id == tenant_id).first()

def create_booking(db: Session, booking_data: schemas.BookingCreateManual, tenant_id: str):
    service = db.query(models.Service).filter(models.Service.id == booking_data.service_id).first()
    if not service: raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    end_time = booking_data.start_time + datetime.timedelta(minutes=service.duration_minutes)
    new_booking = models.Booking(**booking_data.model_dump(), tenant_id=tenant_id, end_time=end_time, booking_type='client')
    db.add(new_booking); db.commit(); db.refresh(new_booking)
    return new_booking

def create_time_block(db: Session, block_data: schemas.TimeBlockCreate, tenant_id: str):
    new_block = models.Booking(**block_data.model_dump(), tenant_id=tenant_id, booking_type='block', status='blocked')
    db.add(new_block); db.commit(); db.refresh(new_block)
    return new_block
    
def update_booking(db: Session, booking_id: int, booking_data: schemas.BookingUpdate, tenant_id: str):
    db_booking = get_booking(db, booking_id, tenant_id)
    if not db_booking: raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    update_data = booking_data.model_dump(exclude_unset=True)
    if db_booking.booking_type == 'client' and ('start_time' in update_data or 'service_id' in update_data):
        service_id = update_data.get('service_id', db_booking.service_id)
        if service_id:
            service = db.query(models.Service).filter(models.Service.id == service_id).first()
            if service:
                start_time = update_data.get('start_time', db_booking.start_time)
                update_data['end_time'] = start_time + datetime.timedelta(minutes=service.duration_minutes)
    for key, value in update_data.items():
        setattr(db_booking, key, value)
    db.commit(); db.refresh(db_booking)
    return db_booking

def delete_booking(db: Session, booking_id: int, tenant_id: str):
    db_booking = get_booking(db, booking_id, tenant_id)
    if not db_booking: raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    db.delete(db_booking); db.commit()

def get_or_create_client_from_bot(db: Session, tenant_id: str, client_data: schemas.BookingCreate):
    client = db.query(models.Client).filter(models.Client.telegram_id == str(client_data.client_telegram_id), models.Client.tenant_id == tenant_id).first()
    if not client:
        client = models.Client(telegram_id=str(client_data.client_telegram_id), first_name=client_data.client_first_name, last_name=client_data.client_last_name, username=client_data.client_username, tenant_id=tenant_id)
        db.add(client); db.commit(); db.refresh(client)
    return client

def create_booking_from_bot(db: Session, booking: models.Booking):
    db.add(booking); db.commit(); db.refresh(booking)
    return booking

def create_broadcast(db: Session, broadcast_data: schemas.BroadcastCreate, tenant_id: str):
    total_recipients = db.query(models.Client).filter(models.Client.tenant_id == tenant_id).count()
    db_broadcast = models.Broadcast(**broadcast_data.model_dump(), tenant_id=tenant_id, total_recipients=total_recipients, status='pending')
    db.add(db_broadcast); db.commit(); db.refresh(db_broadcast)
    return db_broadcast

def get_broadcast_history(db: Session, tenant_id: str):
    return db.query(models.Broadcast).filter(models.Broadcast.tenant_id == tenant_id).order_by(models.Broadcast.created_at.desc()).limit(50).all()

def get_available_slots(db: Session, tenant_id: str, master_id: int, date: datetime.date) -> List[str]:
    master = db.query(models.Master).filter(models.Master.id == master_id, models.Master.tenant_id == tenant_id).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found for this tenant")

    day_name_map = {1: 'monday', 2: 'tuesday', 3: 'wednesday', 4: 'thursday', 5: 'friday', 6: 'saturday', 7: 'sunday'}
    day_name = day_name_map[date.isoweekday()]
    
    schedule = db.query(models.WorkSchedule).filter(models.WorkSchedule.master_id == master_id, models.WorkSchedule.day_of_week == models.DayOfWeekEnum(day_name)).first()
    if not schedule or schedule.is_day_off:
        return []

    work_start_dt = datetime.datetime.combine(date, schedule.start_time)
    work_end_dt = datetime.datetime.combine(date, schedule.end_time)
    
    bookings = db.query(models.Booking).filter(
        models.Booking.master_id == master_id,
        func.date(models.Booking.start_time) == date,
        models.Booking.status != 'canceled'
    ).all()
    
    booked_intervals = [(b.start_time, b.end_time) for b in bookings]
    slot_duration = datetime.timedelta(minutes=30) 
    potential_slot = work_start_dt
    available_slots = []
    
    while potential_slot + slot_duration <= work_end_dt:
        is_available = all(max(potential_slot, start) >= min(potential_slot + slot_duration, end) for start, end in booked_intervals)
        if is_available:
            available_slots.append(potential_slot.strftime("%H:%M"))
        potential_slot += slot_duration
        
    return available_slots
