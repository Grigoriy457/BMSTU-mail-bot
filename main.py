from aiogram import types
import asyncio
import multiprocessing

import config
from dispatcher import bot, dp, DbSessionMiddleware, IgnoreTelegramErrorsMiddleware
import handlers
import workers


async def configure_bot():
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(IgnoreTelegramErrorsMiddleware())

    dp.include_routers(handlers.router)

    await bot.set_my_commands([
        types.bot_command.BotCommand(command=i[0], description=i[1])
        for i in config.COMMANDS
    ])


async def main() -> None:
    schedule_worker_process = multiprocessing.Process(target=workers.start_schedule)
    schedule_worker_process.start()

    await configure_bot()
    await dp.start_polling(bot)

    if schedule_worker_process.is_alive():
        schedule_worker_process.terminate()


if __name__ == "__main__":
    asyncio.run(main())
