# Barbershop booking bot (Telegram)

A Telegram bot that lets clients book an appointment in a few taps. Built as a portfolio project.

## Features

- `/start` - pick a service, a day and a free time slot
- `/my` - see your bookings and cancel any of them
- A time slot can only be booked once
- Optional notification to the owner about every new booking
- Services, prices, working hours and booking window are set in one block at the top of `bot.py`

## Tech

Python, aiogram 3, SQLite.

## Run

```
pip install aiogram
set BOT_TOKEN=your_token_from_BotFather
python bot.py
```

To receive owner notifications, also set `ADMIN_ID` to your Telegram user ID.
