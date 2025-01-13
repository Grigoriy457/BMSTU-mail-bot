from aiogram import Router

from handlers import base_commands, settings, mail


router = Router()
router.include_router(base_commands.router)
router.include_router(settings.router)
router.include_router(mail.router)
