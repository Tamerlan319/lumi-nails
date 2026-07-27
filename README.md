# LUMI NAILS — статический Vercel-проект

Проект не требует npm, Vite или сборщика.

## Локальный запуск
Можно открыть `index.html` через Live Server, либо:

```bash
python -m http.server 5173
```

## Деплой
Загрузите папку в GitHub и импортируйте репозиторий в Vercel. Build Command оставьте пустым.

## Telegram
Добавьте в Vercel Environment Variables:

TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID

Форма `/api/booking` будет присылать заявки в Telegram.
