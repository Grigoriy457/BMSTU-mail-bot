from aiogram import Router, types, F

import database


router = Router()


@router.callback_query(F.data.startswith("settings__notify_with_sound__"))
async def notify_with_sound(callback: types.CallbackQuery, db_session: database.AsyncSession):
    _, _, action = callback.data.split("__")
    tg_user = await db_session.scalar(
        database.select(database.models.TgUser)
        .where(database.models.TgUser.id == callback.from_user.id)
    )
    tg_user.notify_with_sound = (action == "on")
    await db_session.merge(tg_user)
    await db_session.commit()

    if action == "on":
        text = "🔔 Выключить звук уведомлений"
        data = "off"
    else:
        text = "🔔 Включить звук уведомлений"
        data = "on"

    for row in callback.message.reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data.startswith("settings__notify_with_sound__"):
                button.text = text
                button.callback_data = f"settings__notify_with_sound__{data}"

    await callback.answer("✅ Настройки обновлены")
    await callback.message.edit_reply_markup(reply_markup=callback.message.reply_markup)
