from __future__ import annotations

from datetime import date

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from catalog import SERVICES


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✨ Записаться")],
            [KeyboardButton(text="📋 Мои записи")],
        ],
        resize_keyboard=True,
    )


def services_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f'{s["name"]} — {s["price"]} ₽',
                    callback_data=f'service:{s["id"]}',
                )
            ]
            for s in SERVICES
        ] + [[InlineKeyboardButton(text="❌ Отмена", callback_data="flow:cancel")]]
    )


def masters_keyboard(masters: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=m["name"],
                    callback_data=f'master:{m["id"]}',
                )
            ]
            for m in masters
        ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="flow:services")]]
    )


def dates_keyboard(dates: list[date]) -> InlineKeyboardMarkup:
    months = (
        "янв", "фев", "мар", "апр", "май", "июн",
        "июл", "авг", "сен", "окт", "ноя", "дек",
    )
    rows = []
    for d in dates:
        label = f"{d.day} {months[d.month - 1]}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"date:{d.isoformat()}")]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="flow:masters")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def times_keyboard(times: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(times), 3):
        rows.append(
            [
                InlineKeyboardButton(text=t, callback_data=f"time:{t}")
                for t in times[i:i + 3]
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="flow:dates")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить мой номер", request_contact=True)],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="booking:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="flow:cancel"),
            ]
        ]
    )


def cancel_booking_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отменить запись",
                    callback_data=f"cancel_booking:{booking_id}",
                )
            ]
        ]
    )
