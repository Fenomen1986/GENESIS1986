"""Initial migration

Revision ID: d99bb60c5f06
Revises: 
Create Date: 2025-07-17 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd99bb60c5f06'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('tenants',
        sa.Column('id', sa.String(), nullable=False), sa.Column('business_name', sa.String(), nullable=False), sa.Column('bot_token', sa.String(), nullable=True),
        sa.Column('subscription_status', sa.String(), nullable=True), sa.Column('created_at', sa.DateTime(), nullable=True), sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenants_id'), 'tenants', ['id'], unique=False)
    op.create_index(op.f('ix_tenants_subscription_status'), 'tenants', ['subscription_status'], unique=False)
    
    op.create_table('clients',
        sa.Column('id', sa.Integer(), nullable=False), sa.Column('telegram_id', sa.String(), nullable=False), sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True), sa.Column('username', sa.String(), nullable=True), sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True), sa.Column('tags', sa.String(), nullable=True), sa.Column('tenant_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ), sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_telegram_id'), 'clients', ['telegram_id'], unique=True)
    
    op.create_table('masters',
        sa.Column('id', sa.Integer(), nullable=False), sa.Column('name', sa.String(), nullable=False), sa.Column('is_active', sa.Boolean(), nullable=True), sa.Column('tenant_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ), sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_masters_id'), 'masters', ['id'], unique=False)
    
    op.create_table('services',
        sa.Column('id', sa.Integer(), nullable=False), sa.Column('name', sa.String(), nullable=False), sa.Column('price', sa.Float(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False), sa.Column('is_active', sa.Boolean(), nullable=True), sa.Column('tenant_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ), sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_services_id'), 'services', ['id'], unique=False)
    
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False), sa.Column('username', sa.String(), nullable=False), sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False), sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ), sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    op.create_table('broadcasts',
        sa.Column('id', sa.Integer(), nullable=False), sa.Column('tenant_id', sa.String(), nullable=False), sa.Column('message_text', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False), sa.Column('created_at', sa.DateTime(), nullable=True), sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True), sa.Column('total_recipients', sa.Integer(), nullable=True), sa.Column('sent_count', sa.Integer(), nullable=True),
        sa.Column('failed_count', sa.Integer(), nullable=True), sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ), sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_broadcasts_status'), 'broadcasts', ['status'], unique=False)
    
    op.create_table('work_schedules',
        sa.Column('id', sa.Integer(), nullable=False), sa.Column('master_id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Enum('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', name='dayofweek'), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False), sa.Column('end_time', sa.Time(), nullable=False), sa.Column('is_day_off', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['master_id'], ['masters.id'], ), sa.PrimaryKeyConstraint('id')
    )

    op.create_table('bookings',
        sa.Column('id', sa.Integer(), nullable=False), sa.Column('booking_type', sa.String(), nullable=False), sa.Column('title', sa.String(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True), sa.Column('service_id', sa.Integer(), nullable=True), sa.Column('master_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False), sa.Column('start_time', sa.DateTime(), nullable=False), sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ), sa.ForeignKeyConstraint(['master_id'], ['masters.id'], ),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ), sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)
    op.create_index(op.f('ix_bookings_start_time'), 'bookings', ['start_time'], unique=False)
    op.create_index(op.f('ix_bookings_status'), 'bookings', ['status'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_bookings_status'), table_name='bookings'); op.drop_index(op.f('ix_bookings_start_time'), table_name='bookings')
    op.drop_index(op.f('ix_bookings_id'), table_name='bookings'); op.drop_table('bookings'); op.drop_table('work_schedules')
    op.drop_index(op.f('ix_broadcasts_status'), table_name='broadcasts'); op.drop_table('broadcasts'); op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users'); op.drop_table('users'); op.drop_index(op.f('ix_services_id'), table_name='services'); op.drop_table('services')
    op.drop_index(op.f('ix_masters_id'), table_name='masters'); op.drop_table('masters'); op.drop_index(op.f('ix_clients_telegram_id'), table_name='clients'); op.drop_table('clients')
    op.drop_index(op.f('ix_tenants_subscription_status'), table_name='tenants'); op.drop_index(op.f('ix_tenants_id'), table_name='tenants'); op.drop_table('tenants')