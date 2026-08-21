from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TIMEZONE_ALIASES = {
    "Moscow": "Europe/Moscow",
    "MSK": "Europe/Moscow",
    "Москва": "Europe/Moscow",
}


def _parse_admin_ids(raw: str) -> set[int]:
    result: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            result.add(int(part))
    return result


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    timezone: ZoneInfo
    booking_days_ahead: int = 14
    slot_step_minutes: int = 30
    open_time: time = time(10, 0)
    close_time: time = time(20, 0)
    closed_weekdays: tuple[int, ...] = (6,)  # 6 = воскресенье


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Не задан BOT_TOKEN в файле .env")

    tz_name = os.getenv("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow"
    tz_name = TIMEZONE_ALIASES.get(tz_name, tz_name)

    return Settings(
        bot_token=token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        timezone=ZoneInfo(tz_name),
    )
