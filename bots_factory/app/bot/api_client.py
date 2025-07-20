# bots_factory/app/bot/api_client.py

import httpx
import logging
from typing import List, Dict, Any

API_BASE_URL = "http://api:8000/api"

async def get_active_tenants() -> list:
    """Получает список активных клиентов (tenants) с их токенами."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/internal/active-tenants")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logging.error(f"[SYSTEM] Не удалось получить список активных клиентов: {e}")
        return []
    except Exception as e:
        logging.error(f"[SYSTEM] Произошла непредвиденная ошибка при запросе к API: {e}")
        return []

async def get_services(tenant_id: str) -> List[Dict[str, Any]]:
    """Получает список активных услуг для клиента."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/public/{tenant_id}/services")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Ошибка при получении услуг для {tenant_id}: {e}")
            return []

async def get_masters(tenant_id: str) -> List[Dict[str, Any]]:
    """Получает список активных мастеров для клиента."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/public/{tenant_id}/masters")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Ошибка при получении мастеров для {tenant_id}: {e}")
            return []

async def get_available_slots(tenant_id: str, master_id: int, date: str) -> List[str]:
    """Получает список свободных слотов для мастера на конкретную дату."""
    url = f"{API_BASE_URL}/public/{tenant_id}/masters/{master_id}/slots?date={date}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Ошибка при получении слотов: {e}")
            return []

async def create_booking(tenant_id: str, booking_data: Dict[str, Any]) -> bool:
    """Создает новую запись."""
    url = f"{API_BASE_URL}/public/{tenant_id}/bookings"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=booking_data)
            response.raise_for_status()
            return response.status_code == 201
        except Exception as e:
            logging.error(f"Ошибка при создании записи: {e}")
            return False
