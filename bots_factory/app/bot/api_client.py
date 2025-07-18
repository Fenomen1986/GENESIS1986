import httpx
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging

API_URL = "http://api:8000"

class ActiveTenant(BaseModel):
    id: str
    business_name: str
    bot_token: str

class Service(BaseModel):
    id: int
    name: str

class Master(BaseModel):
    id: int
    name: str
    
class Broadcast(BaseModel):
    id: int
    message_text: str

class ApiClient:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, f"{API_URL}{endpoint}", **kwargs)
                response.raise_for_status()
                return response
        except httpx.RequestError as e:
            logging.error(f"[{self.tenant_id or 'SYSTEM'}] Не удалось подключиться к API: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logging.error(f"[{self.tenant_id or 'SYSTEM'}] API вернуло ошибку: {e.response.status_code} - {e.response.text}")
            raise

    @staticmethod
    async def get_active_tenants() -> List[ActiveTenant]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/api/internal/active-tenants")
                response.raise_for_status()
                return [ActiveTenant(**data) for data in response.json()]
        except Exception as e:
            logging.error(f"[SYSTEM] Не удалось получить список активных клиентов: {e}")
            return []

    async def get_services(self) -> List[Service]:
        response = await self._request("GET", f"/api/public/{self.tenant_id}/services")
        return [Service(**s) for s in response.json()]

    async def get_masters(self) -> List[Master]:
        response = await self._request("GET", f"/api/public/{self.tenant_id}/masters")
        return [Master(**m) for m in response.json()]

    async def get_available_slots(self, master_id: int, date: str) -> List[str]:
        response = await self._request("GET", f"/api/public/{self.tenant_id}/masters/{master_id}/slots?date={date}")
        return response.json()

    async def create_booking(self, data: Dict) -> bool:
        try:
            await self._request("POST", f"/api/public/{self.tenant_id}/bookings", json=data)
            return True
        except Exception:
            return False

    async def get_pending_broadcast(self) -> Optional[Broadcast]:
        response = await self._request("GET", f"/api/internal/{self.tenant_id}/pending-broadcast")
        data = response.json()
        return Broadcast(**data) if data else None

    async def get_client_telegram_ids(self) -> List[str]:
        response = await self._request("GET", f"/api/internal/{self.tenant_id}/clients")
        return response.json()

    async def finish_broadcast(self, broadcast_id: int, sent_count: int, failed_count: int):
        await self._request("PUT", f"/api/internal/broadcasts/{broadcast_id}/finish?sent_count={sent_count}&failed_count={failed_count}")