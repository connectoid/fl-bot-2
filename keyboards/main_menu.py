from aiogram.types import (KeyboardButton, Message, ReplyKeyboardMarkup,
                           ReplyKeyboardRemove)

button_1: KeyboardButton = KeyboardButton(text='Биржи')
button_2: KeyboardButton = KeyboardButton(text='Категории')
button_3: KeyboardButton = KeyboardButton(text='Помощь')
button_4: KeyboardButton = KeyboardButton(text='Профиль')

main_menu_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
                                    keyboard=[[button_1, button_2],
                                              [button_3, button_4]],
                                    resize_keyboard=True)