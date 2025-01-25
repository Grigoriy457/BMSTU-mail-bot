from dotenv import dotenv_values, load_dotenv
import logging

load_dotenv("./config/.env", override=True)
config = dotenv_values("./config/.env")

BOT_TOKEN = config["BOT_TOKEN"]

SAMOWARE_CLIENT_NAME = config["SAMOWARE_CLIENT_NAME"]
SAMOWARE_CHECK_INTERVAL_MINUTES = int(config["SAMOWARE_CHECK_INTERVAL_MINUTES"])

DB_HOST = config["DB_HOST"]
DB_NAME = config["DB_NAME"]
DB_USER = config["DB_USER"]
DB_PASSWORD = config["DB_PASSWORD"]

COMMANDS = [
    ("start", "Перезапуск бота"),
    ("check_mail", "Проверить почту"),
    ("settings", "Настройки"),
    ("help", "Помощь"),
]

KEYBOARD_BUTTONS = {
    "settings": "⚙️ Настройки",
    "help": "🆘 Помощь",
}
KEYBOARD_BUTTONS_POSITION = [
    ["settings", "help"],
]

LOGGING_LEVEL = logging.INFO
LOGGING_FORMAT = "%(levelname)s | %(asctime)s | %(name)s (%(filename)s).%(funcName)s(%(lineno)d) -> %(message)s"
LOGGING_DATEFORMAT = "%Y-%m-%d %H:%M:%S"
