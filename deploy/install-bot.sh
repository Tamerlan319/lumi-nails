#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOT_SRC="$PROJECT_ROOT/telegram-bot"
BOT_DIR="/opt/beauty-booking-bot"
SERVICE_NAME="beauty-booking-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Запустите от root: sudo bash deploy/install-bot.sh"
  exit 1
fi

echo "== Проверка доступа к Telegram API =="
if curl -4 -sS --connect-timeout 10 -o /dev/null https://api.telegram.org/; then
  echo "Telegram API доступен."
else
  echo "ВНИМАНИЕ: Telegram API с этого VPS сейчас недоступен."
  echo "Установку можно продолжить, но бот не сможет работать без доступа к api.telegram.org:443."
fi

echo "== Проверка Python =="
if ! command -v python3 >/dev/null 2>&1; then
  apt-get update
  apt-get install -y python3 python3-venv python3-pip
fi

# On some Ubuntu/Debian images python3 exists but venv package is absent.
if ! python3 -m venv --help >/dev/null 2>&1; then
  apt-get update
  apt-get install -y python3-venv
fi

echo "== Системный пользователь =="
if ! id -u beautybot >/dev/null 2>&1; then
  useradd --system --home-dir "$BOT_DIR" --shell /usr/sbin/nologin beautybot
fi

echo "== Копирование бота в $BOT_DIR =="
mkdir -p "$BOT_DIR"

# Preserve production .env and SQLite database on repeat installs.
ENV_BACKUP=""
DB_BACKUP=""
if [[ -f "$BOT_DIR/.env" ]]; then
  ENV_BACKUP="$(mktemp)"
  cp "$BOT_DIR/.env" "$ENV_BACKUP"
fi
if [[ -f "$BOT_DIR/booking.sqlite3" ]]; then
  DB_BACKUP="$(mktemp)"
  cp "$BOT_DIR/booking.sqlite3" "$DB_BACKUP"
fi

find "$BOT_DIR" -mindepth 1 -maxdepth 1 ! -name ".env" ! -name "booking.sqlite3" -exec rm -rf {} +
cp -a "$BOT_SRC"/. "$BOT_DIR"/
rm -f "$BOT_DIR/.env"

if [[ -n "$ENV_BACKUP" ]]; then
  cp "$ENV_BACKUP" "$BOT_DIR/.env"
  rm -f "$ENV_BACKUP"
else
  cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
fi

if [[ -n "$DB_BACKUP" ]]; then
  cp "$DB_BACKUP" "$BOT_DIR/booking.sqlite3"
  rm -f "$DB_BACKUP"
fi

echo "== Python virtualenv =="
python3 -m venv "$BOT_DIR/.venv"
"$BOT_DIR/.venv/bin/pip" install --upgrade pip
"$BOT_DIR/.venv/bin/pip" install -r "$BOT_DIR/requirements.txt"

echo "== Права =="
chown -R beautybot:beautybot "$BOT_DIR"
chmod 600 "$BOT_DIR/.env"

echo "== systemd =="
cp "$PROJECT_ROOT/deploy/beauty-booking-bot.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

TOKEN_LINE="$(grep -E '^BOT_TOKEN=' "$BOT_DIR/.env" || true)"
TOKEN_VALUE="${TOKEN_LINE#BOT_TOKEN=}"

if [[ -z "$TOKEN_VALUE" || "$TOKEN_VALUE" == "PASTE_BOT_TOKEN_HERE" ]]; then
  echo
  echo "Установка завершена, но BOT_TOKEN ещё не указан."
  echo "1) nano $BOT_DIR/.env"
  echo "2) Укажите BOT_TOKEN; ADMIN_IDS пока можно оставить пустым."
  echo "3) systemctl start $SERVICE_NAME"
  echo "4) Напишите боту /id, затем внесите ID в ADMIN_IDS."
  echo "5) systemctl restart $SERVICE_NAME"
else
  systemctl restart "$SERVICE_NAME"
  echo
  echo "Бот установлен и запущен."
  systemctl --no-pager --full status "$SERVICE_NAME" || true
fi

echo
echo "Сайт не изменялся и продолжает работать через nginx отдельно."
