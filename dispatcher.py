from __future__ import annotations

import asyncio
from typing import Callable, Awaitable, Dict, Any

import aiogram
import aiogram.exceptions
from aiogram import Bot, Dispatcher, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import BaseMiddleware
import sqlalchemy.exc

import config
import database


import bot_logger
logger = bot_logger.get_logger("aiogram")


if not config.BOT_TOKEN:
    exit("No token provided")


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: types.TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        async with database.Database() as db:
            async with db.session() as db_session:
                data["db"] = db
                data["db_session"] = db_session
                try:
                    ret = await handler(event, data)
                    await db_session.commit()
                    return ret

                except sqlalchemy.exc.IntegrityError:
                    logger.exception("Data base error")
                    await db_session.rollback()


class IgnoreTelegramErrorsMiddleware(BaseMiddleware):
    async def __call__(self,
                       handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: types.TelegramObject,
                       data: Dict[str, Any]) -> Any:
        try:
            return await handler(event, data)

        except aiogram.exceptions.TelegramForbiddenError:
            if data.get("db_session") is None:
                return

            user_id = (event.message or event.callback_query).from_user.id
            db_user = await data["db_session"].scalar(
                database.select(database.models.TgUser)
                .where(database.models.TgUser.id == user_id)
            )
            db_user.is_deactivated = True
            await data["db_session"].merge(db_user)

        except aiogram.exceptions.TelegramBadRequest as exception:
            patterns = (
                "Bad Request: message is not modified",
                "Bad Request: message can't be edited",
                "Bad Request: message can't be deleted for everyone"
            )
            if any(pattern in str(exception) for pattern in patterns):
                user_id = (event.message or event.callback_query).from_user.id
                logger.warning(f"Error when calling bot handler (id={user_id})", exc_info=True)
                return

            logger.exception("Error when calling bot handler", exc_info=True)


loop = asyncio.get_event_loop()
bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML', link_preview_is_disabled=True))
dp = Dispatcher(storage=MemoryStorage())
