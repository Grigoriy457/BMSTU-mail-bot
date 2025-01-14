from typing import Union
from aiogram import Router, types, F
from aiogram.filters import Command

import config
import database
from handlers.settings import mail_sessions, notify_with_sound


router = Router()
router.include_router(mail_sessions.router)
router.include_router(notify_with_sound.router)


@router.message(Command("settings"))
@router.message(F.text == config.KEYBOARD_BUTTONS["settings"])
@router.callback_query(F.data == "settings")
async def settings(message: Union[types.Message, types.CallbackQuery], db_session: database.AsyncSession):
    tg_user = await db_session.scalar(
        database.select(database.models.TgUser)
        .where(database.models.TgUser.id == message.from_user.id)
    )
    text = "<b>📧 Почтовые ящики</b>\n"\
           "Подключить и отключить почтовые ящики\n\n"\
           "<b>🔔 Вкл/Выкл звук уведомлений</b>\n"\
           "Включение или выключение звука уведомлений телеграма о новых письмах\n\n"\
           "ℹ️ Почта обновляется каждые 10 минут"
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📧 Почтовые ящики", callback_data="settings__mail_sessions")],
        [types.InlineKeyboardButton(
            text=f"🔔 {'Выключить' if tg_user.notify_with_sound else 'Включить'} звук уведомлений",
            callback_data=f"settings__notify_with_sound__{'off' if tg_user.notify_with_sound else 'on'}"
        )]
    ])
    if isinstance(message, types.Message):
        await message.answer(text=text, reply_markup=reply_markup)
    else:
        await message.message.edit_text(text=text, reply_markup=reply_markup)

