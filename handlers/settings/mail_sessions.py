from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup

import config
import database
import samoware


router = Router()


class MailSessionForm(StatesGroup):
    login = State()
    password = State()


@router.callback_query(F.data == "settings__mail_sessions")
async def mail_sessions_handler(callback: types.CallbackQuery, db_session: database.AsyncSession):
    mail_sessions = (await db_session.scalars(
        database.select(database.models.MailSession)
        .where(database.models.MailSession.tg_user_id == callback.from_user.id)
    )).all()
    text = "<b>📧 Почтовые ящики:</b>\n"
    if len(mail_sessions) == 0:
        text += "Почтовые ящики не подключены\n"

    else:
        for i, mail_session in enumerate(mail_sessions):
            text += f"{i + 1}) {mail_session.full_name}\n"

    buttons = [
        [types.InlineKeyboardButton(text="➕ Добавить", callback_data="settings__mail_sessions__add")],
        [types.InlineKeyboardButton(text="◀️ Назад", callback_data="settings")]
    ]
    if len(mail_sessions) > 0:
        buttons[0].append(types.InlineKeyboardButton(text="➖ Удалить", callback_data="settings__mail_sessions__delete"))

    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "settings__mail_sessions__add")
async def add_mail__login(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    new_message = await callback.message.answer("👤 Напиши свой логин")
    await state.set_data({"bot_login_message_id": new_message.message_id})
    await state.set_state(MailSessionForm.login)


@router.message(MailSessionForm.login)
async def add_mail__login_password(message: types.Message, state: FSMContext, bot: Bot):
    new_message = await message.answer(
        "🔑 Напиши свой пароль:\n\n"
        "<i>🛡 Мы гарантируем безопасность твоих данных</i>"
    )
    await bot.edit_message_text(
        text=f"👤 Напиши свой логин\n\n&gt; {message.text}",
        chat_id=message.chat.id,
        message_id=(await state.get_data())["bot_login_message_id"]
    )
    await message.delete()
    await state.update_data({"mail_login": message.text, "bot_password_message_id": new_message.message_id})
    await state.set_state(MailSessionForm.password)


@router.message(MailSessionForm.password)
async def add_mail_password(message: types.Message, state: FSMContext, db_session: database.AsyncSession, bot: Bot):
    state_data = await state.get_data()
    mail_login = state_data["mail_login"]
    mail_password = message.text
    new_message = await message.answer("🔄 Проверка авторизации...")
    await message.delete()
    await bot.delete_message(message.chat.id, state_data["bot_password_message_id"])
    await bot.delete_message(message.chat.id, state_data["bot_login_message_id"])
    await state.clear()

    mail_session = database.models.MailSession(
        tg_user_id=message.from_user.id,
        login=mail_login,
        password=mail_password
    )
    async with samoware.Samoware(mail_session=mail_session) as samoware_mail:
        try:
            await samoware_mail.auth()

            await samoware_mail.send_session_info()
            await samoware_mail.open_folder()

        except samoware.AuthError:
            await new_message.edit_text(
                text="<b>❌ Ошибка авторизации!</b>\nНеверный логин или пароль",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="◀️ Назад", callback_data="settings__mail_sessions")
                ]])
            )
            return

        await db_session.merge(samoware_mail.mail_session)
        await db_session.commit()

        await new_message.edit_text(
            "✅ Почтовый ящик добавлен!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="settings__mail_sessions")
            ]])
        )


@router.callback_query(F.data == "settings__mail_sessions__delete")
async def delete_mail__choose(callback: types.CallbackQuery, db_session: database.AsyncSession):
    mail_sessions = (await db_session.scalars(
        database.select(database.models.MailSession)
        .where(database.models.MailSession.tg_user_id == callback.from_user.id)
    )).all()

    text = "📧 Выбери почтовый ящик для удаления:\n"
    buttons = [
        [types.InlineKeyboardButton(text=f"{i + 1}) {mail_session.full_name}\n", callback_data=f"settings__mail_sessions__delete__{mail_session.id}")]
        for i, mail_session in enumerate(mail_sessions)
    ]
    buttons.append([types.InlineKeyboardButton(text="◀️ Назад", callback_data="settings__mail_sessions")])
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("settings__mail_sessions__delete__"))
async def delete_mail(callback: types.CallbackQuery, db_session: database.AsyncSession):
    _, _, _, mail_session_id = callback.data.split("__")
    mail_session = await db_session.scalar(
        database.select(database.models.MailSession)
        .where(database.models.MailSession.id == mail_session_id)
    )
    if mail_session is not None:
        await db_session.delete(mail_session)
        await db_session.commit()
    await callback.message.edit_text(
        "✅ Почтовый ящик удален",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="settings__mail_sessions")
        ]])
    )
