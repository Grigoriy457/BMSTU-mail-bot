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


async def send_notify(session_id: int, mail: samoware.Mail, chat_id: int, mail_image: BytesIO = None, with_sound: bool = True):
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

        if mail_image is not None:
            try:
                if mail_image.getbuffer().nbytes > 10 * 1024 * 1024:
                    await bot.send_document(
                        chat_id=chat_id,
                        document=types.BufferedInputFile(mail_image.read(), filename="mail_image.png"),
                        caption=text,
                        reply_markup=reply_markup,
                        disable_notification=not with_sound
                    )
                else:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=types.BufferedInputFile(mail_image.read(), filename="mail_image.png"),
                        caption=text,
                        show_caption_above_media=True,
                        reply_markup=reply_markup,
                        disable_notification=not with_sound
                    )
                return
            except (aiogram.exceptions.TelegramBadRequest, aiogram.exceptions.TelegramServerError):
                logger.exception(f"Error while sending notify (mail_session_id={session_id}, mail_uid={mail.uid})")
            except aiogram.exceptions.TelegramForbiddenError:
                return

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
                last_mails = await samoware_mail.sync_mail()

            except samoware.AuthError:
                await samoware_mail.auth()
                await samoware_mail.send_session_info()
                await samoware_mail.open_folder()
                await db_session.merge(samoware_mail.mail_session)
                await db_session.commit()
                last_mails = await samoware_mail.get_last_mail(from_datetime=mail_session.last_mail_datetime)

            samoware_mail.mail_session.last_check = datetime.datetime.now(tz=pytz.UTC)
            await db_session.merge(samoware_mail.mail_session)
            await db_session.commit()
            if len(last_mails) == 0:
                return False

            for last_mail in last_mails:
                if last_mail.is_ssen:
                    continue
                mail_image = None
                try:
                    mail_image = await samoware_mail.get_mail_image(last_mail.uid)
                except OSError as e:
                    logger.exception(f"wkhtmltoimage error (mail_session_id={mail_session.id}, mail_uid={last_mail.uid})")
                await send_notify(
                    mail_session.id,
                    last_mail,
                    chat_id=mail_session.tg_user_id,
                    mail_image=mail_image,
                    with_sound=(await mail_session.awaitable_attrs.tg_user).notify_with_sound
                )

            mail_session.last_mail_datetime = last_mails[-1].send_datetime
            await db_session.merge(mail_session)
            await db_session.commit()

            # for session in (await samoware_mail.get_active_sessions()):
            #     if session.is_tg_bot and (not session.is_my_session):
            #         await samoware_mail.close_session(session_id=session.id)
            return True

    except Exception:
        logger.exception(f"Error while checking mail (mail_session_id={mail_session.id})")
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
