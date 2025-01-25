import asyncio
from aiogram import types
import aiogram.exceptions
from io import BytesIO
from typing import Optional

import datetime
import pytz

import rocketry.conds
from rocketry import Grouper

import config
from dispatcher import bot, logger
import database
import samoware


grouper = Grouper(execution="async")


async def send_notify(session_id: int, mail: samoware.Mail, mail_image: BytesIO, chat_id: int, with_sound: bool = True):
    async with bot.session:
        local_datetime = mail.send_datetime + datetime.timedelta(hours=3)
        text = f"<b>🔔 Новое письмо:</b>\n"\
               f"<b>Тема:</b> {mail.title if mail.title is not None else '—'}\n"\
               f"<b>От:</b> {mail.from_name + ' (' + mail.from_email + ')' if mail.from_name else mail.from_email}\n"\
               f"<b>Дата:</b> {local_datetime.strftime('%d.%m.%Y %H:%M')}\n"
        if "multipart/mixed" in mail.content_type:
            text += "\n<b>📎 Есть вложения</b>\n"
        reply_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Прочитано", callback_data=f"mail__read__{session_id}__{mail.uid}"),
            types.InlineKeyboardButton(text="🗑 Удалить", callback_data=f"mail__delete__{session_id}__{mail.uid}")
        ]])

        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=types.BufferedInputFile(mail_image.read(), filename="image.png"),
                caption=text,
                show_caption_above_media=True,
                reply_markup=reply_markup,
                disable_notification=not with_sound
            )

        except aiogram.exceptions.TelegramBadRequest:
            logger.exception("Error while sending notify")
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                disable_notification=not with_sound
            )


async def check_by_session(mail_session, db_session) -> Optional[bool]:
    try:
        async with samoware.Samoware(mail_session) as samoware_mail:
            try:
                await samoware_mail.open_folder()

            except samoware.AuthError:
                await samoware_mail.auth()
                await samoware_mail.send_session_info()
                await samoware_mail.open_folder()
                await db_session.merge(samoware_mail.mail_session)
                await db_session.commit()


            last_mails = await samoware_mail.get_last_mail(from_datetime=samoware_mail.mail_session.last_mail_datetime)
            samoware_mail.mail_session.last_check = datetime.datetime.now(tz=pytz.UTC)
            await db_session.merge(samoware_mail.mail_session)
            await db_session.commit()
            if len(last_mails) == 0:
                return False

            for last_mail in last_mails[::-1]:
                mail_image = await samoware_mail.get_mail_image(last_mail.uid)
                await send_notify(
                    mail_session.id,
                    last_mail,
                    mail_image=mail_image,
                    chat_id=mail_session.tg_user_id,
                    with_sound=(await mail_session.awaitable_attrs.tg_user).notify_with_sound
                )

            mail_session.last_mail_datetime = last_mails[0].send_datetime
            await db_session.merge(mail_session)
            await db_session.commit()

            # for session in (await samoware_mail.get_active_sessions()):
            #     if session.is_tg_bot and (not session.is_my_session):
            #         await samoware_mail.close_session(session_id=session.id)
            return True

    except Exception:
        logger.exception("Error while checking mail")
        return None


@grouper.task(rocketry.conds.every(f"{config.SAMOWARE_CHECK_INTERVAL_MINUTES} minutes"))
async def check_mail__async():
    async with database.Database() as db:
        async with db.session() as db_session:
            mail_sessions = await db_session.scalars(
                database.select(database.models.MailSession)
            )
            for mail_session in mail_sessions:
                await check_by_session(mail_session=mail_session, db_session=db_session)


def check_mail():
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(check_mail__async())


if __name__ == "__main__":
    check_mail()
