from aiogram import Router, F, types

import database
import samoware


router = Router()


@router.callback_query(F.data.startswith("mail__"))
async def read_mail(callback: types.CallbackQuery, db_session: database.AsyncSession):
    _, action, mail_session_id, mail_uid = callback.data.split("__")
    await callback.answer("🔄 Обработка...")

    mail_session = await db_session.scalar(
        database.select(database.models.MailSession)
        .where(database.models.MailSession.id == int(mail_session_id))
    )
    try:
        async with samoware.Samoware(mail_session) as samoware_mail:
            try:
                await samoware_mail.check_auth()
            except samoware.AuthError:
                await samoware_mail.auth()
                await samoware_mail.send_session_info()
                await samoware_mail.open_folder()
                await db_session.merge(samoware_mail.mail_session)
                await db_session.commit()

            if action == "delete":
                btn_text = "🗑 Удалено"
                await samoware_mail.delete_mail(mail_uid)
            else:
                btn_text = "✅ Прочитано"
                await samoware_mail.read_mail(mail_uid)

        text = callback.message.html_text
        text += f"\n\n<i>&gt; {btn_text}</i>"
        await callback.message.edit_caption(caption=text, show_caption_above_media=True)

    except samoware.RequestError:
        await callback.answer("❌ Ошибка", show_alert=True)
