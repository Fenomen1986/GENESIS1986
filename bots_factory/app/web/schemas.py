from pydantic import BaseModel
import datetime, enum
from typing import List, Optional

class DayOfWeek(str, enum.Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"

class Token(BaseModel):
    access_token: str
    token_type: str

class ServiceBase(BaseModel):
    name: str
    price: float
    duration_minutes: int

class ServiceCreate(ServiceBase):
    pass

class Service(ServiceBase):
    id: int
    is_active: bool
    tenant_id: str
    class Config:
        from_attributes = True

class MasterBase(BaseModel):
    name: str

class MasterCreate(MasterBase):
    pass

class Master(MasterBase):
    id: int
    is_active: bool
    tenant_id: str
    class Config:
        from_attributes = True

class WorkScheduleBase(BaseModel):
    day_of_week: DayOfWeek
    start_time: datetime.time
    end_time: datetime.time
    is_day_off: bool = False

class WorkScheduleCreate(WorkScheduleBase):
    pass

class WorkSchedule(WorkScheduleBase):
    id: int
    master_id: int
    class Config:
        from_attributes = True

class MasterWithSchedule(Master):
    schedules: List[WorkSchedule] = []

class BookingBase(BaseModel):
    start_time: datetime.datetime
    service_id: int
    master_id: int

class BookingCreate(BookingBase):
    client_telegram_id: int
    client_first_name: str
    client_last_name: Optional[str] = None
    client_username: Optional[str] = None

class Booking(BookingBase):
    id: int
    status: str
    end_time: datetime.datetime
    class Config:
        from_attributes = True

class TimeBlockCreate(BaseModel):
    title: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    master_id: int

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    tenant_id: str

class User(UserBase):
    id: int
    tenant_id: str
    class Config:
        from_attributes = True

class TenantBase(BaseModel):
    id: str
    business_name: str

class TenantCreate(TenantBase):
    bot_token: Optional[str] = None
    subscription_status: str = 'trial'
    initial_admin_username: str
    initial_admin_password: str

class Tenant(TenantBase):
    subscription_status: str
    created_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None
    class Config:
        from_attributes = True

# --- Схемы для Настроек (ОБНОВЛЕННЫЕ) ---
class TenantSettingsUpdate(BaseModel):
    business_name: str
    bot_token: Optional[str] = ""
    work_start_time: Optional[datetime.time] = None
    work_end_time: Optional[datetime.time] = None

class TenantSettings(TenantSettingsUpdate):
    id: str
    subscription_status: str
    expires_at: Optional[datetime.datetime] = None
    class Config:
        from_attributes = True

class SuperAdminUser(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class SuperAdminTenant(Tenant):
    users: List[SuperAdminUser] = []
    class Config:
        from_attributes = True

class TenantUpdate(BaseModel):
    business_name: str
    subscription_status: str
    expires_at: Optional[datetime.date] = None

class ClientBase(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    class Config:
        from_attributes = True
        
class PaginatedClients(BaseModel):
    total_count: int
    clients: List[ClientBase]

class ClientUpdate(BaseModel):
    phone_number: Optional[str] = ""
    notes: Optional[str] = ""
    tags: Optional[str] = ""

class ServiceForClientCard(BaseModel):
    name: str
    class Config:
        from_attributes = True

class MasterForClientCard(BaseModel):
    name: str
    class Config:
        from_attributes = True

class BookingForClientCard(BaseModel):
    id: int
    start_time: datetime.datetime
    status: str
    title: Optional[str] = None
    service: Optional[ServiceForClientCard] = None
    master: MasterForClientCard
    class Config:
        from_attributes = True

class ClientDetails(ClientBase):
    phone_number: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    bookings: List[BookingForClientCard] = []

class AnalyticsDataPoint(BaseModel):
    label: str
    value: int

class AnalyticsTimelinePoint(BaseModel):
    date: datetime.date
    count: int

class DashboardAnalytics(BaseModel):
    bookings_timeline: List[AnalyticsTimelinePoint]
    services_distribution: List[AnalyticsDataPoint]

class BroadcastCreate(BaseModel):
    message_text: str

class Broadcast(BroadcastCreate):
    id: int
    status: str
    created_at: datetime.datetime
    total_recipients: int
    sent_count: int
    class Config:
        from_attributes = True