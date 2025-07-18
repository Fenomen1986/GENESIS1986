import asyncio
import logging
import sys
from typing import List, Dict

import httpx
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from pydantic import BaseModel

# Импортируем наши модули из пакета app.bot
from app.bot.handlers import router as main_router
from app.bot.api_client import ApiClient, ActiveTenant

async def broadcast_worker(bot: Bot, tenant_id: str):
    """Фоновый процесс, который ищет и отправляет рассылки."""
    api_client = ApiClient(tenant_id)
    logging.info(f"[{tenant_id}] Worker рассылок запущен.")
    
    while True:
        try:
            broadcast = await api_client.get_pending_broadcast()
            if broadcast:
                logging.info(f"[{tenant_id}] Найдена новая рассылка #{broadcast.id} для отправки.")
                client_ids = await api_client.get_client_telegram_ids()
                
                if not client_ids:
                    logging.warning(f"[{tenant_id}] Рассылка #{broadcast.id} не имеет получателей.")
                    await api_client.finish_broadcast(broadcast.id, 0, 0)
                    continue

                sent_count = 0
                failed_count = 0
                for user_id in client_ids:
                    try:
                        await bot.send_message(user_id, broadcast.message_text)
                        sent_count += 1
                    except (TelegramForbiddenError, TelegramBadRequest):
                        logging.warning(f"[{tenant_id}] Пользователь {user_id} заблокировал бота или чат не найден.")
                        failed_count += 1
                    except Exception as e:
                        logging.error(f"[{tenant_id}] Ошибка отправки сообщения пользователю {user_id}: {e}")
                        failed_count += 1
                    await asyncio.sleep(0.1) # Пауза, чтобы не попасть в лимиты Telegram
                
                await api_client.finish_broadcast(broadcast.id, sent_count, failed_count)
                logging.info(f"[{tenant_id}] Рассылка #{broadcast.id} завершена. Отправлено: {sent_count}, Ошибок: {failed_count}.")

        except Exception as e:
            logging.error(f"[{tenant_id}] Критическая ошибка в worker'е рассылок: {e}")
        
        # Проверять наличие новых рассылок раз в минуту
        await asyncio.sleep(60)

async def start_bot(tenant: ActiveTenant):
    """Инициализирует и запускает один экземпляр бота и связанные с ним фоновые задачи."""
    logging.info(f"Запуск бота для клиента '{tenant.business_name}' (ID: {tenant.id})")
    
    bot = Bot(token=tenant.bot_token)
    # Сохраняем кастомные данные в объекте бота, чтобы иметь к ним доступ в хендлерах
    bot.business_name = tenant.business_name
    bot.tenant_id = tenant.id
    
    dp = Dispatcher()
    dp.include_router(main_router)
    
    # Создаем фоновую задачу для воркера рассылок
    broadcast_task = asyncio.create_task(broadcast_worker(bot, tenant.id))
    
    try:
        # Пропускаем старые обновления, которые могли накопиться, пока бот был выключен
        await bot.delete_webhook(drop_pending_updates=True)
        # Запускаем polling для этого конкретного бота
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка в основном цикле бота для '{tenant.business_name}': {e}")
    finally:
        # При остановке бота (например, по Ctrl+C), отменяем фоновые задачи
        logging.warning(f"Остановка бота для клиента '{tenant.business_name}'.")
        broadcast_task.cancel()
        await bot.session.close()

async def main() -> None:
    """Главная функция, которая управляет жизненным циклом всех ботов."""
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')
    logging.info("Сервис управления ботами запущен.")
    
    running_bots: set[str] = set()
    tasks: Dict[str, asyncio.Task] = {}

    while True:
        logging.info("Проверка активных клиентов из API...")
        try:
            tenants = await ApiClient.get_active_tenants() # Используем статический метод
            active_tenant_ids = {tenant.id for tenant in tenants if tenant.bot_token and "PASTE" not in tenant.bot_token}

            # --- Запускаем новых ботов ---
            for tenant in tenants:
                if tenant.id in active_tenant_ids and tenant.id not in running_bots:
                    logging.info(f"Обнаружен новый активный клиент: '{tenant.business_name}'. Запускаем бота...")
                    task = asyncio.create_task(start_bot(tenant))
                    tasks[tenant.id] = task
                    running_bots.add(tenant.id)

            # --- Останавливаем ботов, которые стали неактивными ---
            for tenant_id in list(running_bots):
                if tenant_id not in active_tenant_ids:
                    logging.warning(f"Клиент '{tenant_id}' стал неактивным. Останавливаем бота...")
                    if tenant_id in tasks:
                        tasks[tenant_id].cancel()
                        del tasks[tenant_id]
                    running_bots.remove(tenant_id)
            
            if not running_bots:
                logging.info("Активных ботов для запуска нет. Следующая проверка через 30 секунд.")

        except Exception as e:
            logging.error(f"Произошла критическая ошибка в главном цикле: {e}")

        # Проверять наличие новых/отключенных клиентов
        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Сервис управления ботами остановлен.")