"""
Telegram-бот для записи клиентов в барбершоп (демо-проект для портфолио).

Что умеет:
  /start  - начать запись: услуга -> день -> время
  /my     - показать мои записи и отменить любую
Записи хранятся в файле bookings.db (SQLite), занятое время второй раз не выдаётся.

Запуск:
  pip install aiogram
  set BOT_TOKEN=токен_от_BotFather      (Windows, cmd)
  python bot.py
"""
import asyncio
import os
import sqlite3
from datetime import date, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

# ---------- Настройки: это меняется под каждого клиента ----------
SERVICES = {"cut": ("Стрижка", 20), "beard": ("Борода", 12), "combo": ("Стрижка + борода", 28)}
TIMES = ["10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]
DAYS_AHEAD = 5  # на сколько дней вперёд можно записаться
ADMIN_ID = os.getenv("ADMIN_ID")  # Telegram ID владельца, ему приходят уведомления (необязательно)

# ---------- База данных ----------
db = sqlite3.connect("bookings.db")
db.execute(
    """CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, user_name TEXT, service TEXT, day TEXT, time TEXT,
        UNIQUE(day, time)   -- одно и то же время нельзя занять дважды
    )"""
)
db.commit()


def free_times(day: str) -> list[str]:
    """Время, которое в этот день ещё никто не занял."""
    taken = {row[0] for row in db.execute("SELECT time FROM bookings WHERE day = ?", (day,))}
    return [t for t in TIMES if t not in taken]


def keyboard(buttons: list[tuple[str, str]], per_row: int = 1) -> InlineKeyboardMarkup:
    """Собирает клавиатуру из пар (текст кнопки, данные кнопки)."""
    row_list = [buttons[i : i + per_row] for i in range(0, len(buttons), per_row)]
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in row_list]
    )


dp = Dispatcher()


# ---------- Шаг 1: выбор услуги ----------
@dp.message(Command("start"))
async def start(message: Message):
    buttons = [(f"{name} - {price} €", f"svc|{key}") for key, (name, price) in SERVICES.items()]
    await message.answer("Привет! Выбери услугу:", reply_markup=keyboard(buttons))


# ---------- Шаг 2: выбор дня ----------
@dp.callback_query(F.data.startswith("svc|"))
async def choose_day(call: CallbackQuery):
    service = call.data.split("|")[1]
    days = [date.today() + timedelta(days=i) for i in range(1, DAYS_AHEAD + 1)]
    buttons = [(d.strftime("%d.%m"), f"day|{service}|{d.isoformat()}") for d in days]
    await call.message.edit_text("Выбери день:", reply_markup=keyboard(buttons, per_row=3))
    await call.answer()


# ---------- Шаг 3: выбор времени ----------
@dp.callback_query(F.data.startswith("day|"))
async def choose_time(call: CallbackQuery):
    _, service, day = call.data.split("|")
    times = free_times(day)
    if not times:
        await call.answer("На этот день всё занято, выбери другой", show_alert=True)
        return
    buttons = [(t, f"time|{service}|{day}|{t}") for t in times]
    await call.message.edit_text("Выбери время:", reply_markup=keyboard(buttons, per_row=3))
    await call.answer()


# ---------- Шаг 4: сохраняем запись ----------
@dp.callback_query(F.data.startswith("time|"))
async def save_booking(call: CallbackQuery, bot: Bot):
    _, service, day, time = call.data.split("|")
    try:
        db.execute(
            "INSERT INTO bookings (user_id, user_name, service, day, time) VALUES (?, ?, ?, ?, ?)",
            (call.from_user.id, call.from_user.full_name, service, day, time),
        )
        db.commit()
    except sqlite3.IntegrityError:  # кто-то успел занять это время раньше
        await call.answer("Это время только что заняли, выбери другое", show_alert=True)
        return

    name, price = SERVICES[service]
    nice_day = date.fromisoformat(day).strftime("%d.%m")
    await call.message.edit_text(f"Готово! {name}, {nice_day} в {time}. Цена: {price} €.\nМои записи: /my")
    await call.answer()
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"Новая запись: {call.from_user.full_name}, {name}, {nice_day} {time}")


# ---------- Мои записи и отмена ----------
@dp.message(Command("my"))
async def my_bookings(message: Message):
    rows = db.execute(
        "SELECT id, service, day, time FROM bookings WHERE user_id = ? AND day >= ? ORDER BY day, time",
        (message.from_user.id, date.today().isoformat()),
    ).fetchall()
    if not rows:
        await message.answer("У тебя нет записей. Записаться: /start")
        return
    buttons = [
        (f"Отменить: {SERVICES[s][0]}, {date.fromisoformat(d).strftime('%d.%m')} {t}", f"del|{bid}")
        for bid, s, d, t in rows
    ]
    await message.answer("Твои записи (нажми, чтобы отменить):", reply_markup=keyboard(buttons))


@dp.callback_query(F.data.startswith("del|"))
async def cancel_booking(call: CallbackQuery):
    booking_id = int(call.data.split("|")[1])
    # user_id в условии нужен, чтобы нельзя было отменить чужую запись
    db.execute("DELETE FROM bookings WHERE id = ? AND user_id = ?", (booking_id, call.from_user.id))
    db.commit()
    await call.message.edit_text("Запись отменена. Записаться заново: /start")
    await call.answer()


async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("Не задан BOT_TOKEN. Получи токен у @BotFather и задай переменную окружения.")
    await dp.start_polling(Bot(token))


if __name__ == "__main__":
    asyncio.run(main())
