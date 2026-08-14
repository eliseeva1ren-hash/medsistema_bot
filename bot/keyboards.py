"""
Инлайн- и обычные клавиатуры, которые видит клиент.
"""
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from bot.doctors import DIRECTIONS, SPECIALTIES


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Записаться на приём", callback_data="start_booking")]
        ]
    )


def directions_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"dir:{key}")]
        for key, label in DIRECTIONS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def specialties_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"spec:{key}")]
        for key, label in SPECIALTIES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_yes"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm_edit"),
            ]
        ]
    )


def edit_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ФИО", callback_data="edit:full_name")],
            [InlineKeyboardButton(text="Дата рождения", callback_data="edit:birth_date")],
            [InlineKeyboardButton(text="Телефон", callback_data="edit:phone")],
            [InlineKeyboardButton(text="Направление / врач", callback_data="edit:direction")],
            [InlineKeyboardButton(text="Дата приёма", callback_data="edit:appointment_dt")],
            [InlineKeyboardButton(text="⬅️ Назад, всё верно", callback_data="edit_back")],
        ]
    )
