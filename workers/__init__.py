import logging
from rocketry import Rocketry
import datetime
import pytz

import bot_logger
from workers import mail_checker, sessions_updater


def start_schedule():
    bot_logger.get_logger("rocketry.task", level=logging.WARNING)

    schedule = Rocketry(
        time_func=lambda: (datetime.datetime.now(pytz.utc) + datetime.timedelta(hours=3)).timestamp(),
        config={
            "silence_task_prerun": True,
            "silence_task_logging": True,
            "silence_cond_check": True,
        },
    )

    schedule.include_grouper(mail_checker.grouper)
    schedule.include_grouper(sessions_updater.grouper)

    schedule.run()

    logger = bot_logger.get_logger("rocketry.main")
    logger.warning("[-] SCHEDULE worker stopped!")


if __name__ == "__main__":
    start_schedule()
