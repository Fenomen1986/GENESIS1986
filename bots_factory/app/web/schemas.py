# bots_factory/app/web/schemas.py

from pydantic import BaseModel, Field
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
    is_active: bool = True
    class Config:
        from_attributes = True

class MasterCreate(MasterBase):
    pass

class MasterUpdate(MasterBase):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class Master(MasterBase):
    id: int
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
    class Config:
        from_attributes = True

class BookingBase(BaseModel):
    start_time: datetime.datetime
    service_id: Optional[int] = None
    master_id: int

class BookingCreate(BookingBase):
    client_telegram_id: int
    client_first_name: str
    client_last_name: Optional[str] = None
    client_username: Optional[str] = None

class BookingCreateManual(BaseModel):
    client_id: int
    service_id: int
    master_id: int
    start_time: datetime.datetime

class BookingUpdate(BaseModel):
    service_id: Optional[int] = None
    master_id: Optional[int] = None
    client_id: Optional[int] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    status: Optional[str] = None
    title: Optional[str] = None
    booking_type: Optional[str] = None

class ClientForBooking(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    class Config:
        from_attributes = True

class Booking(BookingBase):
    id: int
    status: str
    end_time: datetime.datetime
    tenant_id: str
    booking_type: str
    client_id: Optional[int] = None
    title: Optional[str] = None
    created_at: datetime.datetime
    service: Optional[Service] = None
    master: Optional[Master] = None
    client: Optional[ClientForBooking] = None
    class Config:
        from_attributes = True

class TimeBlockCreate(BaseModel):
    title: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    master_id: int

class TenantSettingsUpdate(BaseModel):
    business_name: str
    bot_token: Optional[str] = ""
    work_start_time: Optional[datetime.time] = None
    work_end_time: Optional[datetime.time] = None

class TenantSettings(TenantSettingsUpdate):
    id: str
    class Config:
        from_attributes = True

class ClientBase(BaseModel):
    id: int
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone_number: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime.datetime
    class Config:
        from_attributes = True
        
class PaginatedClients(BaseModel):
    total_count: int
    clients: List[ClientBase]

class ClientUpdate(BaseModel):
    phone_number: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None

class BookingForClientCard(BaseModel):
    id: int
    start_time: datetime.datetime
    status: str
    title: Optional[str] = None
    service: Optional[Service] = None
    master: Master
    booking_type: str
    class Config:
        from_attributes = True

class ClientDetails(ClientBase):
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

class ClientCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    username: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    
class BroadcastHistory(Broadcast):
    pass