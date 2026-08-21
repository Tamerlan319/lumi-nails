from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties

from catalog import master_by_id, masters_for_service, service_by_id
from config import Settings, load_settings
from db import (
    bookings_for_date,
    cancel_booking,
    create_booking,
    due_reminders,
    has_overlap,
    init_db,
    mark_reminder_sent,
    user_bookings,
)
from keyboards import (
    cancel_booking_keyboard,
    confirm_keyboard,
    dates_keyboard,
    main_menu,
    masters_keyboard,
    phone_keyboard,
    services_keyboard,
    times_keyboard,
)
from states import BookingState

router = Router()
settings: Settings

PHONE_RE = re.compile(r"^\+?[0-9][0-9 ()-]{8,18}[0-9]$")


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y в %H:%M")


def local_now() -> datetime:
    return datetime.now(settings.timezone)


def next_booking_dates() -> list[date]:
    result: list[date] = []
    today = local_now().date()
    for offset in range(settings.booking_days_ahead):
        d = today + timedelta(days=offset)
        if d.weekday() in settings.closed_weekdays:
            continue
        result.append(d)
    return result


def combine_local(d: date, hhmm: str) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return datetime(
        d.year, d.month, d.day, hour, minute,
        tzinfo=settings.timezone,
    )


async def available_times(
    d: date,
    master_id: int,
    duration_minutes: int,
) -> list[str]:
    result: list[str] = []
    cursor = datetime(
        d.year, d.month, d.day,
        settings.open_time.hour, settings.open_time.minute,
        tzinfo=settings.timezone,
    )
    close_dt = datetime(
        d.year, d.month, d.day,
        settings.close_time.hour, settings.close_time.minute,
        tzinfo=settings.timezone,
    )

    now = local_now()

    while cursor + timedelta(minutes=duration_minutes) <= close_dt:
        end_at = cursor + timedelta(minutes=duration_minutes)

        if cursor > now + timedelta(minutes=15):
            if not await has_overlap(master_id, cursor, end_at):
                result.append(cursor.strftime("%H:%M"))

        cursor += timedelta(minutes=settings.slot_step_minutes)

    return result


async def notify_admins(bot: Bot, text: str) -> None:
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logging.exception("Не удалось отправить уведомление администратору %s", admin_id)


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(
        "Ваш Telegram ID: <code>"
        f"{message.from_user.id}"
        "</code>\n\n"
        "Добавьте это число в ADMIN_IDS в файле .env."
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Здравствуйте! 👋\n\n"
        "Я помогу выбрать услугу, мастера и свободное время.",
        reply_markup=main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cancel_flow_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Запись отменена.", reply_markup=main_menu())


@router.callback_query(F.data == "flow:cancel")
async def cancel_flow_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Запись отменена.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()


@router.message(F.text == "✨ Записаться")
@router.message(Command("book"))
async def start_booking(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(BookingState.choosing_service)
    await message.answer("Выберите услугу:", reply_markup=services_keyboard())


@router.callback_query(F.data == "flow:services")
async def back_to_services(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BookingState.choosing_service)
    await callback.message.edit_text("Выберите услугу:", reply_markup=services_keyboard())
    await callback.answer()


@router.callback_query(BookingState.choosing_service, F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
    service_id = int(callback.data.split(":", 1)[1])
    service = service_by_id(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    masters = masters_for_service(service_id)
    if not masters:
        await callback.answer("Для услуги пока нет мастеров", show_alert=True)
        return

    await state.update_data(service_id=service_id)
    await state.set_state(BookingState.choosing_master)

    await callback.message.edit_text(
        f'Услуга: <b>{service["name"]}</b>\n'
        f'Длительность: {service["duration"]} мин.\n'
        f'Стоимость: {service["price"]} ₽\n\n'
        "Выберите мастера:",
        reply_markup=masters_keyboard(masters),
    )
    await callback.answer()


@router.callback_query(F.data == "flow:masters")
async def back_to_masters(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    service_id = data.get("service_id")
    if not service_id:
        await state.set_state(BookingState.choosing_service)
        await callback.message.edit_text("Выберите услугу:", reply_markup=services_keyboard())
        await callback.answer()
        return

    masters = masters_for_service(int(service_id))
    await state.set_state(BookingState.choosing_master)
    await callback.message.edit_text("Выберите мастера:", reply_markup=masters_keyboard(masters))
    await callback.answer()


@router.callback_query(BookingState.choosing_master, F.data.startswith("master:"))
async def choose_master(callback: CallbackQuery, state: FSMContext) -> None:
    master_id = int(callback.data.split(":", 1)[1])
    master = master_by_id(master_id)
    data = await state.get_data()

    if not master or int(data["service_id"]) not in master["service_ids"]:
        await callback.answer("Мастер недоступен для этой услуги", show_alert=True)
        return

    await state.update_data(master_id=master_id)
    await state.set_state(BookingState.choosing_date)

    await callback.message.edit_text(
        f'Мастер: <b>{master["name"]}</b>\n\nВыберите дату:',
        reply_markup=dates_keyboard(next_booking_dates()),
    )
    await callback.answer()


@router.callback_query(F.data == "flow:dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BookingState.choosing_date)
    await callback.message.edit_text(
        "Выберите дату:",
        reply_markup=dates_keyboard(next_booking_dates()),
    )
    await callback.answer()


@router.callback_query(BookingState.choosing_date, F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext) -> None:
    selected_date = date.fromisoformat(callback.data.split(":", 1)[1])

    if selected_date not in next_booking_dates():
        await callback.answer("Эта дата уже недоступна", show_alert=True)
        return

    data = await state.get_data()
    service = service_by_id(int(data["service_id"]))
    master_id = int(data["master_id"])

    times = await available_times(selected_date, master_id, int(service["duration"]))
    if not times:
        await callback.answer("На этот день свободного времени нет", show_alert=True)
        return

    await state.update_data(date=selected_date.isoformat())
    await state.set_state(BookingState.choosing_time)

    await callback.message.edit_text(
        f"Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
        "Выберите свободное время:",
        reply_markup=times_keyboard(times),
    )
    await callback.answer()


@router.callback_query(BookingState.choosing_time, F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext) -> None:
    selected_time = callback.data.split(":", 1)[1]
    data = await state.get_data()

    selected_date = date.fromisoformat(data["date"])
    service = service_by_id(int(data["service_id"]))
    master_id = int(data["master_id"])

    times = await available_times(selected_date, master_id, int(service["duration"]))
    if selected_time not in times:
        await callback.answer("Это время уже занято. Выберите другое.", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=times_keyboard(times))
        return

    await state.update_data(time=selected_time)
    await state.set_state(BookingState.entering_name)

    await callback.message.edit_text(
        f"Вы выбрали {selected_date.strftime('%d.%m.%Y')} в {selected_time}.\n\n"
        "Как вас зовут?"
    )
    await callback.answer()


@router.message(BookingState.entering_name, F.text)
async def enter_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2 or len(name) > 60:
        await message.answer("Введите имя длиной от 2 до 60 символов.")
        return

    await state.update_data(client_name=name)
    await state.set_state(BookingState.entering_phone)
    await message.answer(
        "Отправьте номер телефона кнопкой ниже или введите его вручную:",
        reply_markup=phone_keyboard(),
    )


async def save_phone_and_show_confirmation(message: Message, state: FSMContext, phone: str) -> None:
    data = await state.get_data()
    service = service_by_id(int(data["service_id"]))
    master = master_by_id(int(data["master_id"]))
    selected_date = date.fromisoformat(data["date"])
    selected_time = data["time"]

    await state.update_data(phone=phone)
    await state.set_state(BookingState.confirming)

    await message.answer(
        "Проверьте запись:\n\n"
        f'✨ <b>{service["name"]}</b>\n'
        f'👤 Мастер: <b>{master["name"]}</b>\n'
        f'📅 {selected_date.strftime("%d.%m.%Y")} в {selected_time}\n'
        f'⏱ {service["duration"]} мин.\n'
        f'💳 {service["price"]} ₽\n'
        f'🙋 {data["client_name"]}\n'
        f'📱 {phone}',
        reply_markup=confirm_keyboard(),
    )


@router.message(BookingState.entering_phone, F.contact)
async def enter_phone_contact(message: Message, state: FSMContext) -> None:
    # Разрешаем использовать свой контакт. Если Telegram прислал user_id,
    # проверяем, что это контакт самого отправителя.
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Пожалуйста, отправьте свой номер телефона.")
        return

    await save_phone_and_show_confirmation(message, state, message.contact.phone_number)


@router.message(BookingState.entering_phone, F.text)
async def enter_phone_text(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if phone == "❌ Отмена":
        await state.clear()
        await message.answer("Запись отменена.", reply_markup=main_menu())
        return

    if not PHONE_RE.fullmatch(phone):
        await message.answer(
            "Не удалось распознать номер. Пример: +7 999 123-45-67"
        )
        return

    await save_phone_and_show_confirmation(message, state, phone)


@router.callback_query(BookingState.confirming, F.data == "booking:confirm")
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    service = service_by_id(int(data["service_id"]))
    master = master_by_id(int(data["master_id"]))
    selected_date = date.fromisoformat(data["date"])
    start_at = combine_local(selected_date, data["time"])
    end_at = start_at + timedelta(minutes=int(service["duration"]))

    booking_id = await create_booking(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        client_name=data["client_name"],
        phone=data["phone"],
        service_id=int(service["id"]),
        service_name=service["name"],
        master_id=int(master["id"]),
        master_name=master["name"],
        start_at=start_at,
        end_at=end_at,
    )

    if booking_id is None:
        await state.set_state(BookingState.choosing_time)
        times = await available_times(
            selected_date,
            int(master["id"]),
            int(service["duration"]),
        )
        await callback.message.edit_text(
            "К сожалению, это время только что заняли.\n"
            "Выберите другое свободное время:",
            reply_markup=times_keyboard(times),
        )
        await callback.answer("Время уже занято", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Запись подтверждена!</b>\n\n"
        f'Номер записи: <b>#{booking_id}</b>\n'
        f'{service["name"]} — {master["name"]}\n'
        f'{fmt_dt(start_at)}\n\n'
        "Если планы изменятся, запись можно отменить в разделе «Мои записи»."
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu())

    admin_text = (
        "🆕 <b>Новая запись</b>\n\n"
        f"#{booking_id}\n"
        f'{service["name"]}\n'
        f'Мастер: {master["name"]}\n'
        f'Дата: {fmt_dt(start_at)}\n'
        f'Клиент: {data["client_name"]}\n'
        f'Телефон: {data["phone"]}\n'
        f'Telegram: @{callback.from_user.username or "нет username"}'
    )
    await notify_admins(bot, admin_text)
    await callback.answer()


@router.message(F.text == "📋 Мои записи")
@router.message(Command("my"))
async def my_bookings(message: Message) -> None:
    rows = await user_bookings(message.from_user.id, local_now())
    if not rows:
        await message.answer("У вас нет предстоящих записей.", reply_markup=main_menu())
        return

    await message.answer("Ваши предстоящие записи:")
    for row in rows:
        start = datetime.fromisoformat(row["start_at"])
        await message.answer(
            f'#{row["id"]} — <b>{row["service_name"]}</b>\n'
            f'Мастер: {row["master_name"]}\n'
            f'{fmt_dt(start)}',
            reply_markup=cancel_booking_keyboard(int(row["id"])),
        )


@router.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_user_booking(callback: CallbackQuery, bot: Bot) -> None:
    booking_id = int(callback.data.split(":", 1)[1])
    row = await cancel_booking(booking_id, callback.from_user.id)

    if not row:
        await callback.answer("Запись уже отменена или не найдена", show_alert=True)
        return

    start = datetime.fromisoformat(row["start_at"])
    await callback.message.edit_text(
        f'❌ Запись #{booking_id} отменена.\n'
        f'{row["service_name"]}, {fmt_dt(start)}'
    )

    await notify_admins(
        bot,
        "❌ <b>Клиент отменил запись</b>\n\n"
        f'#{booking_id}\n'
        f'{row["service_name"]}\n'
        f'Мастер: {row["master_name"]}\n'
        f'Дата: {fmt_dt(start)}\n'
        f'Клиент: {row["client_name"]}\n'
        f'Телефон: {row["phone"]}',
    )
    await callback.answer("Запись отменена")


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def admin_day(message: Message, day: date) -> None:
    if not is_admin(message.from_user.id):
        return

    rows = await bookings_for_date(day.isoformat())
    if not rows:
        await message.answer(f"На {day.strftime('%d.%m.%Y')} записей нет.")
        return

    lines = [f"<b>Записи на {day.strftime('%d.%m.%Y')}</b>\n"]
    for row in rows:
        start = datetime.fromisoformat(row["start_at"])
        lines.append(
            f'#{row["id"]} {start.strftime("%H:%M")} — '
            f'{row["service_name"]}, {row["master_name"]}\n'
            f'{row["client_name"]}, {row["phone"]}'
        )
    await message.answer("\n\n".join(lines))


@router.message(Command("today"))
async def admin_today(message: Message) -> None:
    await admin_day(message, local_now().date())


@router.message(Command("tomorrow"))
async def admin_tomorrow(message: Message) -> None:
    await admin_day(message, local_now().date() + timedelta(days=1))


@router.message(Command("admin_cancel"))
async def admin_cancel(message: Message, bot: Bot) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /admin_cancel 123")
        return

    booking_id = int(parts[1])
    row = await cancel_booking(booking_id)
    if not row:
        await message.answer("Активная запись не найдена.")
        return

    await message.answer(f"Запись #{booking_id} отменена.")
    try:
        await bot.send_message(
            int(row["user_id"]),
            f'❌ Администратор отменил вашу запись #{booking_id} '
            f'({row["service_name"]}).\n'
            "Свяжитесь с салоном или выберите другое время.",
        )
    except Exception:
        logging.exception("Не удалось уведомить клиента об отмене")


async def reminder_worker(bot: Bot) -> None:
    while True:
        try:
            now = local_now()
            until = now + timedelta(hours=24)
            rows = await due_reminders(now, until)

            for row in rows:
                start = datetime.fromisoformat(row["start_at"])
                try:
                    await bot.send_message(
                        int(row["user_id"]),
                        "⏰ <b>Напоминание о записи</b>\n\n"
                        f'{row["service_name"]}\n'
                        f'Мастер: {row["master_name"]}\n'
                        f'{fmt_dt(start)}',
                    )
                    await mark_reminder_sent(int(row["id"]))
                except Exception:
                    logging.exception(
                        "Не удалось отправить напоминание по записи #%s",
                        row["id"],
                    )
        except Exception:
            logging.exception("Ошибка reminder_worker")

        await asyncio.sleep(300)


async def main() -> None:
    global settings
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()
    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    reminder_task = asyncio.create_task(reminder_worker(bot))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
