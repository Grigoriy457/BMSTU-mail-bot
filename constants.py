from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import config


main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=config.KEYBOARD_BUTTONS[button_type])
            for button_type in buttons_type
        ]
        for buttons_type in config.KEYBOARD_BUTTONS_POSITION],
    resize_keyboard=True,
    selective=True,
    is_persistent=True
)
