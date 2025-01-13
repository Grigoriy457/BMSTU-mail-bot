import asyncio
from aiogram import types
from io import BytesIO

import datetime
import pytz
import sqlalchemy

import rocketry.conds
from rocketry import Grouper

from dispatcher import bot, logger
import database
import samoware


grouper = Grouper(execution="async")


@grouper.task(rocketry.conds.every("5 minutes"))
async def update_sessions__async():
    async with database.Database() as db:
        async with db.session() as db_session:
            mail_sessions = await db_session.scalars(
                database.select(database.models.MailSession)
                .where(database.models.MailSession.update_session_at <= datetime.datetime.now(pytz.UTC))
            )
            for mail_session in mail_sessions:
                try:
                    async with samoware.Samoware(mail_session) as samoware_mail:
                        try:
                            await samoware_mail.logout()

                        except samoware.AuthError:
                            pass

                        finally:
                            await samoware_mail.auth()
                            await samoware_mail.send_session_info()
                            await samoware_mail.open_folder()
                            await db_session.merge(samoware_mail.mail_session)
                            await db_session.commit()

                except Exception:
                    logger.exception("Error while updating mail session")


@grouper.task(rocketry.conds.every("2 minute"))
async def close_other_sessions__async():
    async with database.Database() as db:
        async with db.session() as db_session:
            mail_sessions = await db_session.scalars(database.select(database.models.MailSession))
            for mail_session in mail_sessions:
                try:
                    async with samoware.Samoware(mail_session) as samoware_mail:
                        active_sessions = await samoware_mail.get_active_sessions()
                        for session in active_sessions:
                            if session.is_tg_bot and (not session.is_my_session):
                                await samoware_mail.close_session(session_id=session.id)

                except Exception:
                    logger.exception("Error while checking active mail sessions")


def update_sessions():
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(update_sessions__async())


def close_other_sessions():
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(close_other_sessions__async())


if __name__ == "__main__":
    close_other_sessions()
