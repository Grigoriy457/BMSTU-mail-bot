from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

import datetime
import pytz
from typing import Optional

import config
import database
from dispatcher import logger
from constants import main_keyboard
from workers import mail_checker


router = Router()


@router.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext, db_session: database.AsyncSession, db: database.Database, bot: Bot):
    logger.info(f"[HANDLER] Start command (id={message.from_user.id})", extra={"tg_user_id": message.from_user.id})
    await state.clear()
    await db.add_tg_user(message.from_user.id, message.from_user.username)

    await message.answer(
<<<<<<< HEAD
        "👋 Привет! Я буду тебя уведомлять о новых письмах, которые ты получишь в своем почтовом ящике.",
=======
        "👋 Привет! Я буду тебя уведомлять о новых письмах, которые ты получаешь в своем почтовом ящике.",
>>>>>>> 6aef4e855c7b17f0105f8f1d087a24d154ccd566
        reply_markup=main_keyboard
    )

    mail_session = await db_session.scalar(
        database.select(database.models.MailSession)
        .where(database.models.MailSession.tg_user_id == message.from_user.id)
    )
    if mail_session is None:
        await message.answer(
            "Для начала подключи свой почтовый ящик 👇",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="📧 Подключить почту", callback_data="settings__mail_sessions__add")
            ]])
        )


@router.message(Command("help"))
@router.message(F.text == config.KEYBOARD_BUTTONS["help"])
async def help_handler(message: types.Message):
    logger.info(f"[HANDLER] Help command (id={message.from_user.id})", extra={"tg_user_id": message.from_user.id})
    await message.answer(
        "Нашёл ошибку или есть вопрос, обращайся к <a href='https://t.me/Grigoriy234'>Грише</a>",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="🆘 Помощь", url="https://t.me/Grigoriy234")
        ]])
    )


@router.message(Command("check_mail"))
async def check_mail_choose(message: types.Message, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Check mail command (id={message.from_user.id})", extra={"tg_user_id": message.from_user.id})

    mail_sessions = (await db_session.scalars(
        database.select(database.models.MailSession)
        .where(database.models.MailSession.tg_user_id == message.from_user.id)
    )).all()
    if len(mail_sessions) == 0:
        await message.answer("📧 Ты ещё не подключил почтовые ящики")
        return
    if len(mail_sessions) == 1:
        await check_mail(None, db_session, mail_sessions[0], message)
        return

    await message.answer(
        "📧 Выбери почтовый ящик для проверки",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=mail_session.full_name, callback_data=f"check_mail__{mail_session.id}")]
            for mail_session in mail_sessions
        ])
    )


@router.callback_query(F.data.startswith("check_mail__"))
async def check_mail(callback: Optional[types.CallbackQuery], db_session: database.AsyncSession, mail_session: database.models.MailSession = None, message: types.Message = None):
    if mail_session is None:
        _, mail_session_id = callback.data.split("__")
        mail_session = await db_session.scalar(
            database.select(database.models.MailSession)
            .where(database.models.MailSession.id == mail_session_id)
        )
        if mail_session is None:
            await callback.message.edit_text("❌ Почтовый ящик не найден")
            return

    if (datetime.datetime.now(tz=pytz.UTC) - mail_session.last_check.replace(tzinfo=pytz.UTC)) <= datetime.timedelta(minutes=1):
        text = "❌ Почта уже проверялась меньше минуты назад!"
        if message is not None:
            await message.answer(text)
        else:
            await callback.message.edit_text(text, reply_markup=main_keyboard)
        return

    if message is not None:
        new_message = await message.answer("📧 Проверка почты...")
    else:
        new_message = callback.message
        await callback.message.edit_text("📧 Проверка почты...")

    status = await mail_checker.check_by_session(mail_session=mail_session, db_session=db_session)
    if status is None:
        await new_message.edit_text("❌ Ошибка при проверке почты")
        return
    await new_message.edit_text("✅ Почта проверена!")
