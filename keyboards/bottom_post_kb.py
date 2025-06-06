from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_bottom_keyboard(id: int = None, *buttons: str) -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    kb_builder.row(*[InlineKeyboardButton(
        text=button,
        callback_data=f'{button}_{id}') for button in buttons])
    return kb_builder.as_markup()


def create_exchange_keyboard(*buttons: str) -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    kb_builder.row(*[InlineKeyboardButton(
        text=button,
        callback_data=f'{button}') for button in buttons],
        width=1)
    return kb_builder.as_markup()
