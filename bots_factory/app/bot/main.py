# bots_factory/app/bot/main.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from typing import Callable, Dict, Any, Awaitable
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject

# Исправленные абсолютные импорты
from app.bot.handlers import router
from app.bot import api_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

class TenantMiddleware(BaseMiddleware):
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["tenant_id"] = self.tenant_id
        return await handler(event, data)

async def run_bot(token: str, tenant_id: str):
    """Запускает и управляет одним экземпляром бота."""
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.update.middleware(TenantMiddleware(tenant_id=tenant_id))
    dp.include_router(router)
    
    logging.info(f"Бот для клиента '{tenant_id}' запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка в работе бота для клиента '{tenant_id}': {e}")
    finally:
        logging.warning(f"Бот для клиента '{tenant_id}' остановлен.")

async def main():
    """Главная функция, которая опрашивает API и управляет ботами."""
    logging.info("Сервис управления ботами запущен.")
    running_bots = {}

    while True:
        logging.info("Проверка активных клиентов из API...")
        active_tenants = await api_client.get_active_tenants()
        
        if not active_tenants:
            logging.info("Активных ботов для запуска нет.")
        else:
            active_tenant_ids = {tenant['id'] for tenant in active_tenants}
            
            # Останавливаем ботов, которых больше нет в активном списке
            for tenant_id, task in list(running_bots.items()):
                if tenant_id not in active_tenant_ids:
                    logging.info(f"Останавливаем бота для неактивного клиента '{tenant_id}'...")
                    task.cancel()
                    del running_bots[tenant_id]

            # Запускаем новых ботов
            for tenant in active_tenants:
                tenant_id = tenant['id']
                token = tenant.get('bot_token')
                if tenant_id not in running_bots and token:
                    task = asyncio.create_task(run_bot(token, tenant_id))
                    running_bots[tenant_id] = task
        
        await asyncio.sleep(30) # Пауза перед следующей проверкой

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Сервис остановлен вручную.")
