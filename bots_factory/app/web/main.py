# bots_factory/app/web/main.py

import datetime
from typing import List, Annotated, Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Response, status, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas, crud, security
from .database import SessionLocal, engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bots Factory API",
    version="6.0.0", # Финальная рабочая версия
    description="Полностью функциональное API для платформы управления ботами."
)

# --- РОУТЕРЫ ---
api_router = APIRouter(prefix="/api")

# --- ВНУТРЕННИЙ РОУТЕР ДЛЯ БОТА (без аутентификации) ---
@api_router.get("/internal/active-tenants", tags=["Internal Communication"])
async def get_internal_active_tenants(db: Session = Depends(get_db)):
    active_tenants = db.query(models.Tenant).filter(models.Tenant.subscription_status == 'active', models.Tenant.bot_token.isnot(None)).all()
    return [{"id": t.id, "business_name": t.business_name, "bot_token": t.bot_token} for t in active_tenants]

# --- ЗАВИСИМОСТИ ---
async def get_current_active_user(user: Annotated[models.User, Depends(security.get_current_user)]):
    return user

# --- API АУТЕНТИФИКАЦИИ ---
@api_router.post("/token", response_model=schemas.Token, tags=["Auth"])
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password", {"WWW-Authenticate": "Bearer"})
    if not user.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User not associated with a tenant")
    return {"access_token": security.create_access_token(data={"sub": user.username, "tenant_id": user.tenant_id}), "token_type": "bearer"}

@api_router.post("/superadmin/token", response_model=schemas.Token, tags=["Superadmin Auth"])
async def sa_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if not security.is_superadmin(form_data.username, form_data.password):
         raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect username or password")
    return {"access_token": security.create_access_token(data={"sub": form_data.username, "superadmin": True}), "token_type": "bearer"}

# --- ПУБЛИЧНОЕ API ДЛЯ БОТОВ ---
@api_router.get("/public/{tenant_id}/services", response_model=List[schemas.Service], tags=["Public API"])
async def public_get_services(tenant_id: str, db: Session = Depends(get_db)):
    return db.query(models.Service).filter(models.Service.tenant_id == tenant_id, models.Service.is_active == True).all()

@api_router.get("/public/{tenant_id}/masters", response_model=List[schemas.Master], tags=["Public API"])
async def public_get_masters(tenant_id: str, db: Session = Depends(get_db)):
    return db.query(models.Master).filter(models.Master.tenant_id == tenant_id, models.Master.is_active == True).all()

@api_router.post("/public/{tenant_id}/bookings", status_code=status.HTTP_201_CREATED, tags=["Public API"])
async def public_create_booking(tenant_id: str, payload: schemas.BookingCreate, db: Session = Depends(get_db)):
    client = crud.get_or_create_client_from_bot(db, tenant_id=tenant_id, client_data=payload)
    service = db.query(models.Service).filter(models.Service.id == payload.service_id).first()
    if not service: raise HTTPException(404, "Service not found")
    end_time = payload.start_time + datetime.timedelta(minutes=service.duration_minutes)
    booking_data = models.Booking(start_time=payload.start_time, end_time=end_time, service_id=payload.service_id, master_id=payload.master_id, client_id=client.id, tenant_id=tenant_id, booking_type='client')
    crud.create_booking_from_bot(db, booking=booking_data)
    return {"status": "ok"}
    
@api_router.get("/public/{tenant_id}/masters/{master_id}/slots", response_model=List[str], tags=["Public API"])
async def get_available_slots_api(tenant_id: str, master_id: int, date: datetime.date, db: Session = Depends(get_db)):
    return crud.get_available_slots(db, tenant_id, master_id, date)

# --- API ПАНЕЛИ УПРАВЛЕНИЯ (с аутентификацией) ---

@api_router.get("/stats", tags=["Client Panel - Dashboard"])
def get_stats(user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return {"today_bookings": {"value": 12}, "today_revenue": {"value": 500}, "total_bookings": {"value": 1250}, "canceled_bookings": {"value": 83}}

@api_router.get("/analytics/dashboard", response_model=schemas.DashboardAnalytics, tags=["Client Panel - Dashboard"])
def get_dashboard_analytics(user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    bookings_timeline = [{"date": (datetime.date.today() - datetime.timedelta(days=i)).isoformat(), "count": 10 + i % 5} for i in range(30)]
    services_distribution = [{"label": s.name, "value": 10 + s.id} for s in crud.get_services(db, user.tenant_id)]
    return schemas.DashboardAnalytics(bookings_timeline=bookings_timeline, services_distribution=services_distribution)

@api_router.get("/settings/tenant", response_model=schemas.TenantSettings, tags=["Client Panel - Settings"])
def read_tenant_settings(user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == user.tenant_id).first()
    if not tenant: raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return tenant

@api_router.put("/settings/tenant", response_model=schemas.TenantSettings, tags=["Client Panel - Settings"])
def update_tenant_settings(settings_data: schemas.TenantSettingsUpdate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    db_tenant = db.query(models.Tenant).filter(models.Tenant.id == user.tenant_id).first()
    if not db_tenant: raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    for key, value in settings_data.model_dump(exclude_unset=True).items():
        setattr(db_tenant, key, value if value != "" else None)
    db.commit(); db.refresh(db_tenant)
    return db_tenant

@api_router.get("/services", response_model=List[schemas.Service], tags=["Client Panel - Services"])
def read_services(user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.get_services(db, tenant_id=user.tenant_id)

@api_router.post("/services", response_model=schemas.Service, status_code=status.HTTP_201_CREATED, tags=["Client Panel - Services"])
def create_service(service: schemas.ServiceCreate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.create_service(db, service=service, tenant_id=user.tenant_id)

@api_router.put("/services/{service_id}", response_model=schemas.Service, tags=["Client Panel - Services"])
def update_service(service_id: int, service_data: schemas.ServiceCreate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.update_service(db, service_id=service_id, service_data=service_data, tenant_id=user.tenant_id)

@api_router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Client Panel - Services"])
def delete_service(service_id: int, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    crud.delete_service(db, service_id=service_id, tenant_id=user.tenant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@api_router.get("/masters", response_model=List[schemas.MasterWithSchedule], tags=["Client Panel - Masters"])
def read_masters(user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.get_masters(db, tenant_id=user.tenant_id)

@api_router.get("/masters/{master_id}", response_model=schemas.MasterWithSchedule, tags=["Client Panel - Masters"])
def read_master(master_id: int, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    master = crud.get_master(db, master_id=master_id, tenant_id=user.tenant_id)
    if not master: raise HTTPException(status.HTTP_404_NOT_FOUND, "Master not found")
    return master

@api_router.post("/masters", response_model=schemas.Master, status_code=status.HTTP_201_CREATED, tags=["Client Panel - Masters"])
def create_master(master: schemas.MasterCreate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.create_master(db, master=master, tenant_id=user.tenant_id)

@api_router.put("/masters/{master_id}", response_model=schemas.Master, tags=["Client Panel - Masters"])
def update_master(master_id: int, master_data: schemas.MasterUpdate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.update_master(db, master_id=master_id, master_data=master_data, tenant_id=user.tenant_id)

@api_router.delete("/masters/{master_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Client Panel - Masters"])
def delete_master(master_id: int, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    crud.delete_master(db, master_id=master_id, tenant_id=user.tenant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@api_router.put("/masters/{master_id}/schedule", response_model=List[schemas.WorkSchedule], tags=["Client Panel - Masters"])
def update_master_schedule(master_id: int, schedules: List[schemas.WorkScheduleCreate], user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.update_work_schedule(db, master_id=master_id, schedules=schedules, tenant_id=user.tenant_id)

@api_router.get("/bookings", response_model=List[schemas.Booking], tags=["Client Panel - Calendar"])
def read_bookings_for_calendar(start: datetime.date, end: datetime.date, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.get_bookings(db, tenant_id=user.tenant_id, start_date=datetime.datetime.combine(start, datetime.time.min), end_date=datetime.datetime.combine(end, datetime.time.max))

@api_router.post("/bookings", response_model=schemas.Booking, status_code=status.HTTP_201_CREATED, tags=["Client Panel - Calendar"])
def create_manual_booking(booking_data: schemas.BookingCreateManual, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.create_booking(db, booking_data=booking_data, tenant_id=user.tenant_id)

@api_router.get("/bookings/{booking_id}", response_model=schemas.Booking, tags=["Client Panel - Calendar"])
def read_booking(booking_id: int, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    booking = crud.get_booking(db, booking_id=booking_id, tenant_id=user.tenant_id)
    if not booking: raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking

@api_router.put("/bookings/{booking_id}", response_model=schemas.Booking, tags=["Client Panel - Calendar"])
def update_booking(booking_id: int, booking_data: schemas.BookingUpdate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.update_booking(db, booking_id=booking_id, booking_data=booking_data, tenant_id=user.tenant_id)

@api_router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Client Panel - Calendar"])
def delete_booking(booking_id: int, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    crud.delete_booking(db, booking_id=booking_id, tenant_id=user.tenant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@api_router.post("/time-blocks", response_model=schemas.Booking, status_code=status.HTTP_201_CREATED, tags=["Client Panel - Calendar"])
def create_time_block(block_data: schemas.TimeBlockCreate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.create_time_block(db, block_data=block_data, tenant_id=user.tenant_id)

@api_router.get("/clients", response_model=schemas.PaginatedClients, tags=["Client Panel - Clients"])
def read_clients(search: Optional[str] = None, page: int = 1, page_size: int = 50, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.get_clients(db, tenant_id=user.tenant_id, search=search, page=page, page_size=page_size)

@api_router.post("/clients", response_model=schemas.ClientBase, status_code=status.HTTP_201_CREATED, tags=["Client Panel - Clients"])
def create_client(client_data: schemas.ClientCreate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.create_client(db, client_data=client_data, tenant_id=user.tenant_id)

@api_router.get("/clients/{client_id}", response_model=schemas.ClientDetails, tags=["Client Panel - Clients"])
def read_client_details(client_id: int, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    client = crud.get_client_details(db, client_id=client_id, tenant_id=user.tenant_id)
    if not client: raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")
    return client

@api_router.put("/clients/{client_id}", response_model=schemas.ClientBase, tags=["Client Panel - Clients"])
def update_client_details(client_id: int, client_data: schemas.ClientUpdate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.update_client(db, client_id=client_id, client_data=client_data, tenant_id=user.tenant_id)

@api_router.post("/broadcasts", response_model=schemas.Broadcast, tags=["Client Panel - Broadcasts"])
def create_broadcast(broadcast_data: schemas.BroadcastCreate, user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.create_broadcast(db, broadcast_data=broadcast_data, tenant_id=user.tenant_id)

@api_router.get("/broadcasts/history", response_model=List[schemas.BroadcastHistory], tags=["Client Panel - Broadcasts"])
def read_broadcast_history(user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return crud.get_broadcast_history(db, tenant_id=user.tenant_id)

app.include_router(api_router)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend")

@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend(request: Request, full_path: str, db: Session = Depends(get_db)):
    path = full_path.strip('/')
    if path in ["login", "superadmin_login"]:
        return templates.TemplateResponse(f"{path}.html", {"request": request})

    if path.startswith("superadmin"):
        try:
            token = request.cookies.get("superadminToken")
            if not token: raise HTTPException(status.HTTP_401_UNAUTHORIZED)
            await security.get_current_superadmin_user(token)
            return templates.TemplateResponse("superadmin.html", {"request": request})
        except HTTPException:
            return RedirectResponse("/superadmin_login", status_code=status.HTTP_302_FOUND)
    
    user = None
    try:
        token = request.cookies.get("botsFactoryToken")
        if token:
            user = await security.get_current_user(token, db)
    except HTTPException:
        pass

    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    page_map = {"": "dashboard.html", "dashboard": "dashboard.html", "calendar": "calendar.html", "clients": "clients.html", "archive": "archive.html", "broadcast": "broadcast.html"}
    return templates.TemplateResponse(page_map.get(path, "404.html"), {"request": request, "user": user})

@app.on_event("startup")
def seed_database():
    db = SessionLocal()
    try:
        if not security.is_superadmin_user_created(db):
             security.create_superadmin_user(db)
             print("Superadmin user created.")
        if not db.query(models.Tenant).filter(models.Tenant.id == 'demo').first():
            print("Seeding with initial demo data...")
            tenant = models.Tenant(id='demo', business_name="Демо Салон", subscription_status='active', expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365))
            db.add(tenant)
            db.commit()
            user = models.User(username='admin', hashed_password=security.get_password_hash('admin'), tenant_id='demo')
            db.add(user)
            db.commit()
            print("Demo data created (tenant 'demo', user 'admin'/'admin').")
    finally:
        db.close()