# bots_factory/app/web/models.py

from sqlalchemy import (Column, Integer, String, DateTime, Float, ForeignKey,
                        Boolean, Time, Enum as EnumDB)
from sqlalchemy.orm import relationship, declarative_base
import datetime
import enum

Base = declarative_base()

class DayOfWeekEnum(enum.Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"

class Tenant(Base):
    __tablename__ = 'tenants'
    id = Column(String, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    bot_token = Column(String, nullable=True)
    subscription_status = Column(String, default='trial', index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    work_start_time = Column(Time, nullable=True)
    work_end_time = Column(Time, nullable=True)
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    services = relationship("Service", back_populates="tenant", cascade="all, delete-orphan")
    masters = relationship("Master", back_populates="tenant", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="tenant", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="tenant", cascade="all, delete-orphan")
    broadcasts = relationship("Broadcast", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=True)
    tenant = relationship("Tenant", back_populates="users")

class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=False)
    tenant = relationship("Tenant", back_populates="services")

class Master(Base):
    __tablename__ = 'masters'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=False)
    tenant = relationship("Tenant", back_populates="masters")
    schedules = relationship("WorkSchedule", back_populates="master", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="master", cascade="all, delete-orphan")

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=False)
    tenant = relationship("Tenant", back_populates="clients")
    bookings = relationship("Booking", back_populates="client", cascade="all, delete-orphan")

class WorkSchedule(Base):
    __tablename__ = 'work_schedules'
    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey('masters.id'), nullable=False)
    day_of_week = Column(EnumDB(DayOfWeekEnum, name="day_of_week_enum"), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_day_off = Column(Boolean, default=False)
    master = relationship("Master", back_populates="schedules")

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True, index=True)
    booking_type = Column(String, default='client', nullable=False)
    title = Column(String, nullable=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=True)
    master_id = Column(Integer, ForeignKey('masters.id'), nullable=False)
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, default='confirmed', index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    tenant = relationship("Tenant", back_populates="bookings")
    client = relationship("Client", back_populates="bookings")
    service = relationship("Service")
    master = relationship("Master", back_populates="bookings")

class Broadcast(Base):
    __tablename__ = 'broadcasts'
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), ForeignKey('tenants.id'), nullable=False)
    message_text = Column(String, nullable=False)
    status = Column(String, default='pending', nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    tenant = relationship("Tenant", back_populates="broadcasts")