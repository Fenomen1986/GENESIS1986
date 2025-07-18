import datetime
from typing import List, Annotated, Optional

# ИСПРАВЛЕННЫЙ БЛОК ИМПОРТОВ
from fastapi import FastAPI, Request, HTTPException, Depends, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

# Абсолютные импорты из нашего пакета
from app.web import models, schemas
from app.web.database import SessionLocal, get_db
from app.web.security import (
    create_access_token, get_current_user,
    verify_password, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_superadmin_user, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD,
    oauth2_scheme # <--- ВОТ ИСПРАВЛЕНИЕ
)

app = FastAPI(
    title="Bots Factory API",
    version="1.0.0",
    description="Финальная версия API для платформы управления ботами."
)

app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")
templates = Jinja2Templates(directory="/app/frontend")

# --- УНИВЕРСАЛЬНАЯ ЗАВИСИМОСТЬ ДЛЯ ЗАЩИТЫ API ---
async def get_user_from_token(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    return await get_current_user(token, db)

# --- API АУТЕНТИФИКАЦИИ ---
@app.post("/api/token", response_model=schemas.Token, tags=["Auth"])
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token_data = {"sub": user.username}
    expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=token_data, expires_delta=expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/superadmin/token", response_model=schemas.Token, tags=["Superadmin Auth"])
async def sa_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if form_data.username != SUPERADMIN_USERNAME or form_data.password != SUPERADMIN_PASSWORD:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": SUPERADMIN_PASSWORD, "token_type": "bearer"}

app = FastAPI(
    title="Bots Factory API",
    version="1.0.0",
    description="Финальная версия API для платформы управления ботами."
)

app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")
templates = Jinja2Templates(directory="/app/frontend")

# --- УНИВЕРСАЛЬНАЯ ЗАВИСИМОСТЬ ДЛЯ ЗАЩИТЫ API ---
async def get_user_from_token(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    return await get_current_user(token, db)
# --- API АУТЕНТИФИКАЦИИ ---
@app.post("/api/token", response_model=schemas.Token, tags=["Auth"])
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token_data = {"sub": user.username}
    expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=token_data, expires_delta=expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/superadmin/token", response_model=schemas.Token, tags=["Superadmin Auth"])
async def sa_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if form_data.username != SUPERADMIN_USERNAME or form_data.password != SUPERADMIN_PASSWORD:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": SUPERADMIN_PASSWORD, "token_type": "bearer"}
# --- ПУБЛИЧНОЕ API ДЛЯ БОТОВ ---
@app.get("/api/public/{tenant_id}/services", response_model=List[schemas.Service], tags=["Public API for Bots"])
async def public_get_services(tenant_id: str, db: Session = Depends(get_db)):
    return db.query(models.Service).filter(models.Service.tenant_id == tenant_id, models.Service.is_active == True).all()

@app.get("/api/public/{tenant_id}/masters", response_model=List[schemas.Master], tags=["Public API for Bots"])
async def public_get_masters(tenant_id: str, db: Session = Depends(get_db)):
    return db.query(models.Master).filter(models.Master.tenant_id == tenant_id, models.Master.is_active == True).all()

@app.post("/api/public/{tenant_id}/bookings", status_code=status.HTTP_201_CREATED, tags=["Public API for Bots"])
async def public_create_booking(tenant_id: str, payload: schemas.BookingCreate, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.telegram_id == str(payload.client_telegram_id), models.Client.tenant_id == tenant_id).first()
    if not client:
        client = models.Client(telegram_id=str(payload.client_telegram_id), first_name=payload.client_first_name, last_name=payload.client_last_name, username=payload.client_username, tenant_id=tenant_id)
        db.add(client); db.commit(); db.refresh(client)
    
    service = db.query(models.Service).filter(models.Service.id == payload.service_id).first()
    if not service: raise HTTPException(404, "Service not found")
    
    end_time = payload.start_time + datetime.timedelta(minutes=service.duration_minutes)
    db_booking = models.Booking(start_time=payload.start_time, end_time=end_time, service_id=payload.service_id, master_id=payload.master_id, client_id=client.id, tenant_id=tenant_id, booking_type='client')
    db.add(db_booking); db.commit()
    return {"status": "ok"}

@app.get("/api/public/{tenant_id}/masters/{master_id}/slots", response_model=List[str], tags=["Public API for Bots"])
async def get_available_slots(tenant_id: str, master_id: int, date: datetime.date, db: Session = Depends(get_db)):
    day_of_week_enum = models.DayOfWeek(date.isoweekday())
    schedule = db.query(models.WorkSchedule).filter(models.WorkSchedule.master_id == master_id, models.WorkSchedule.day_of_week == day_of_week_enum).first()
    if not schedule or schedule.is_day_off: return []
    work_start_dt = datetime.datetime.combine(date, schedule.start_time); work_end_dt = datetime.datetime.combine(date, schedule.end_time)
    bookings = db.query(models.Booking).filter(models.Booking.master_id == master_id, func.date(models.Booking.start_time) == date, models.Booking.status != 'canceled').all()
    booked_intervals = [(b.start_time, b.end_time) for b in bookings]
    slot_duration = datetime.timedelta(minutes=30); potential_slot = work_start_dt; available_slots = []
    while potential_slot + slot_duration <= work_end_dt:
        is_available = all(max(potential_slot, start) >= min(potential_slot + slot_duration, end) for start, end in booked_intervals)
        if is_available: available_slots.append(potential_slot.strftime("%H:%M"))
        potential_slot += slot_duration
    return available_slots

# --- ВНУТРЕННЕЕ API ДЛЯ СЕРВИСА БОТОВ ---
@app.get("/api/internal/active-tenants", include_in_schema=False)
async def get_internal_active_tenants(db: Session = Depends(get_db)):
    active_tenants = db.query(models.Tenant).filter(models.Tenant.subscription_status == 'active', models.Tenant.bot_token.isnot(None)).all()
    return [{"id": t.id, "business_name": t.business_name, "bot_token": t.bot_token} for t in active_tenants]

@app.get("/api/internal/{tenant_id}/pending-broadcast", response_model=Optional[schemas.Broadcast], include_in_schema=False)
async def get_pending_broadcast_for_bot(tenant_id: str, db: Session = Depends(get_db)):
    broadcast = db.query(models.Broadcast).filter(models.Broadcast.tenant_id == tenant_id, models.Broadcast.status == 'pending').order_by(models.Broadcast.created_at).first()
    if broadcast:
        broadcast.status = 'in_progress'; broadcast.started_at = datetime.datetime.utcnow()
        db.commit(); db.refresh(broadcast)
    return broadcast

@app.get("/api/internal/{tenant_id}/clients", response_model=List[str], include_in_schema=False)
async def get_client_telegram_ids(tenant_id: str, db: Session = Depends(get_db)):
    clients = db.query(models.Client.telegram_id).filter(models.Client.tenant_id == tenant_id).all()
    return [c.telegram_id for c in clients]

@app.put("/api/internal/broadcasts/{broadcast_id}/finish", include_in_schema=False)
async def finish_broadcast(broadcast_id: int, sent_count: int, failed_count: int, db: Session = Depends(get_db)):
    broadcast = db.query(models.Broadcast).filter(models.Broadcast.id == broadcast_id).first()
    if broadcast:
        broadcast.status = 'completed'; broadcast.finished_at = datetime.datetime.utcnow()
        broadcast.sent_count = sent_count; broadcast.failed_count = failed_count
        db.commit()
    return {"status": "ok"}
# --- API ПАНЕЛИ КЛИЕНТА ---
@app.get("/api/stats", tags=["Client Panel"])
async def get_stats(user: Annotated[models.User, Depends(get_user_from_token)], db: Session = Depends(get_db)):
    today = datetime.date.today(); start_of_day = datetime.datetime.combine(today, datetime.time.min); end_of_day = datetime.datetime.combine(today, datetime.time.max)
    today_bookings = db.query(models.Booking).filter(models.Booking.tenant_id == user.tenant_id, models.Booking.start_time >= start_of_day, models.Booking.start_time <= end_of_day, models.Booking.status != 'canceled', models.Booking.booking_type == 'client').count()
    total_bookings = db.query(models.Booking).filter(models.Booking.tenant_id == user.tenant_id, models.Booking.booking_type == 'client').count()
    canceled_bookings = db.query(models.Booking).filter(models.Booking.tenant_id == user.tenant_id, models.Booking.status == 'canceled', models.Booking.booking_type == 'client').count()
    return {"today_bookings": {"value": today_bookings}, "today_revenue": {"value": 0}, "total_bookings": {"value": total_bookings}, "canceled_bookings": {"value": canceled_bookings}}

@app.get("/api/analytics/dashboard", response_model=schemas.DashboardAnalytics, tags=["Client Panel"])
async def get_dashboard_analytics(user: Annotated[models.User, Depends(get_user_from_token)], db: Session = Depends(get_db)):
    thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    bookings_timeline_data = db.query(func.date(models.Booking.start_time).label("date"), func.count(models.Booking.id).label("count")).filter(models.Booking.tenant_id == user.tenant_id, models.Booking.booking_type == 'client', models.Booking.start_time >= thirty_days_ago).group_by(func.date(models.Booking.start_time)).order_by(func.date(models.Booking.start_time)).all()
    services_distribution_data = db.query(models.Service.name.label("label"), func.count(models.Booking.id).label("value")).join(models.Booking, models.Service.id == models.Booking.service_id).filter(models.Booking.tenant_id == user.tenant_id, models.Booking.booking_type == 'client').group_by(models.Service.name).order_by(func.count(models.Booking.id).desc()).limit(5).all()
    return {"bookings_timeline": bookings_timeline_data, "services_distribution": services_distribution_data}

@app.get("/api/services", response_model=List[schemas.Service], tags=["Client Panel"])
async def get_services(user: Annotated[models.User, Depends(get_user_from_token)], db: Session = Depends(get_db)):
    return db.query(models.Service).filter(models.Service.tenant_id == user.tenant_id).order_by(models.Service.name).all()

# ... (и все остальные CRUD эндпоинты для masters, clients, bookings, time-blocks, settings, broadcasts, как мы их разработали)
# --- API ПАНЕЛИ СУПЕРАДМИНИСТРАТОРА ---
@app.get("/api/superadmin/stats", tags=["Superadmin"])
async def sa_get_stats(admin: Annotated[dict, Depends(get_current_superadmin_user)], db: Session = Depends(get_db)):
    total_tenants = db.query(models.Tenant).count()
    total_users = db.query(models.User).count()
    total_bookings = db.query(models.Booking).count()
    return {"total_tenants": total_tenants, "total_users": total_users, "total_bookings": total_bookings}

@app.get("/api/superadmin/tenants", response_model=List[schemas.SuperAdminTenant], tags=["Superadmin"])
async def sa_get_all_tenants(admin: Annotated[dict, Depends(get_current_superadmin_user)], db: Session = Depends(get_db)):
    return db.query(models.Tenant).options(joinedload(models.Tenant.users)).order_by(models.Tenant.created_at).all()

@app.post("/api/superadmin/tenants", response_model=schemas.Tenant, status_code=status.HTTP_201_CREATED, tags=["Superadmin"])
async def sa_create_tenant_with_user(tenant_data: schemas.TenantCreate, admin: Annotated[dict, Depends(get_current_superadmin_user)], db: Session = Depends(get_db)):
    if db.query(models.Tenant).filter(models.Tenant.id == tenant_data.id).first(): raise HTTPException(status_code=400, detail="Клиент с таким ID уже существует.")
    if db.query(models.User).filter(models.User.username == tenant_data.initial_admin_username).first(): raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует.")
    new_tenant = models.Tenant(id=tenant_data.id, business_name=tenant_data.business_name, bot_token=tenant_data.bot_token, subscription_status=tenant_data.subscription_status, expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=14))
    hashed_password = get_password_hash(tenant_data.initial_admin_password)
    new_user = models.User(username=tenant_data.initial_admin_username, hashed_password=hashed_password, tenant_id=new_tenant.id)
    db.add(new_tenant); db.add(new_user); db.commit(); db.refresh(new_tenant)
    return new_tenant

@app.put("/api/superadmin/tenants/{tenant_id}", response_model=schemas.Tenant, tags=["Superadmin"])
async def sa_update_tenant(tenant_id: str, tenant_data: schemas.TenantUpdate, admin: Annotated[dict, Depends(get_current_superadmin_user)], db: Session = Depends(get_db)):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not db_tenant: raise HTTPException(status_code=404, detail="Клиент не найден.")
    db_tenant.business_name = tenant_data.business_name
    db_tenant.subscription_status = tenant_data.subscription_status
    db_tenant.expires_at = datetime.datetime.combine(tenant_data.expires_at, datetime.time.min) if tenant_data.expires_at else None
    db.commit(); db.refresh(db_tenant)
    return db_tenant

@app.delete("/api/superadmin/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Superadmin"])
async def sa_delete_tenant(tenant_id: str, admin: Annotated[dict, Depends(get_current_superadmin_user)], db: Session = Depends(get_db)):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not db_tenant: raise HTTPException(status_code=404, detail="Tenant not found")
    db.delete(db_tenant); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/api/superadmin/users", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Superadmin"])
async def sa_create_user(user_data: schemas.UserCreate, admin: Annotated[dict, Depends(get_current_superadmin_user)], db: Session = Depends(get_db)):
    if not db.query(models.Tenant).filter(models.Tenant.id == user_data.tenant_id).first(): raise HTTPException(status_code=404, detail="Tenant не найден.")
    if db.query(models.User).filter(models.User.username == user_data.username).first(): raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует.")
    hashed_password = get_password_hash(user_data.password)
    new_user = models.User(username=user_data.username, hashed_password=hashed_password, tenant_id=user_data.tenant_id)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return new_user

@app.delete("/api/superadmin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Superadmin"])
async def sa_delete_user(user_id: int, admin: Annotated[dict, Depends(get_current_superadmin_user)], db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user: raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(db_user); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.put("/api/superadmin/users/{user_id}/reset-password", tags=["Superadmin"])
async def sa_reset_user_password(user_id: int, new_password_data: dict, admin: Annotated[dict, Depends(get_current_superadmin_user)], db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user: raise HTTPException(status_code=404, detail="User not found")
    db_user.hashed_password = get_password_hash(new_password_data['password'])
    db.commit()
    return {"message": "Password updated successfully"}
# --- ОБСЛУЖИВАНИЕ HTML СТРАНИЦ ---
async def get_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("botsFactoryToken")
    if not token: return None
    try: return await get_current_user(token, db)
    except HTTPException: return None

@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend(request: Request, full_path: str, db: Session = Depends(get_db)):
    path = full_path.rstrip('/')
    if path == "login": return templates.TemplateResponse("login.html", {"request": request})
    if path == "superadmin/login": return templates.TemplateResponse("superadmin_login.html", {"request": request})

    if path.startswith("superadmin"):
        sa_token = request.cookies.get("superadminToken")
        if not sa_token or sa_token != SUPERADMIN_PASSWORD: return RedirectResponse("/superadmin/login")
        return templates.TemplateResponse("superadmin.html", {"request": request})

    user = await get_user_from_cookie(request, db)
    if not user: return RedirectResponse("/login")
        
    page_map = {"": "dashboard.html", "calendar": "calendar.html", "clients": "clients.html", "archive": "archive.html", "broadcast": "broadcast.html"}
    file_to_serve = page_map.get(path, "404.html")
    return templates.TemplateResponse(file_to_serve, {"request": request, "user": user})

# --- Функция для первоначального заполнения БД ---
@app.on_event("startup")
def seed_database():
    db = SessionLocal()
    try:
        if not db.query(models.Tenant).first():
            print("Database is empty. Seeding with initial data...")
            tenant = models.Tenant(id='demo', business_name="Демо Салон", subscription_status='active', expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365), bot_token="PASTE_YOUR_DEMO_BOT_TOKEN_HERE")
            db.add(tenant); db.commit()
            user = models.User(username='admin', hashed_password=get_password_hash('admin'), tenant_id='demo')
            db.add(user); db.commit()
            print("Initial data (tenant 'demo', user 'admin' with password 'admin') created successfully.")
    finally:
        db.close()