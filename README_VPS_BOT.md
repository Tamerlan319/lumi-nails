# LUMI NAILS + Telegram booking bot на одном VPS

В архиве сайт и Telegram-бот находятся в одном исходном проекте, но **на сервере запускаются отдельно**:

- сайт продолжает обслуживаться вашим существующим nginx;
- бот устанавливается в `/opt/beauty-booking-bot`;
- бот запускается отдельным `systemd`-сервисом `beauty-booking-bot`;
- `.env` бота не находится в публичной папке сайта, поэтому токен Telegram нельзя скачать через браузер.

Это сделано специально: помещать `BOT_TOKEN` внутрь `/var/www/...`, который отдаёт nginx, небезопасно.

## 1. Сначала проверьте Telegram с VPS

Из корня проекта:

```bash
bash deploy/check-telegram.sh
```

Если `api.telegram.org` отвечает и порт 443 доступен, бот сможет работать на этом VPS.

## 2. Установка бота

```bash
sudo bash deploy/install-bot.sh
```

Скрипт:
- создаст системного пользователя `beautybot`;
- скопирует код в `/opt/beauty-booking-bot`;
- создаст Python virtualenv;
- установит зависимости;
- подключит systemd;
- не затронет nginx и работающий сайт;
- при повторной установке сохранит `.env` и `booking.sqlite3`.

## 3. Настройка

Откройте:

```bash
sudo nano /opt/beauty-booking-bot/.env
```

Минимально:

```env
BOT_TOKEN=токен_из_BotFather
ADMIN_IDS=
TIMEZONE=Europe/Moscow
```

ADMIN_IDS сначала можно оставить пустым.

Запустите:

```bash
sudo systemctl restart beauty-booking-bot
```

Затем откройте вашего бота в Telegram и отправьте:

```text
/id
```

Бот вернёт ваш числовой Telegram ID. Впишите его:

```env
ADMIN_IDS=123456789
```

Для нескольких администраторов:

```env
ADMIN_IDS=123456789,987654321
```

И перезапустите:

```bash
sudo systemctl restart beauty-booking-bot
```

## 4. Проверка

```bash
sudo systemctl status beauty-booking-bot --no-pager
```

Логи:

```bash
sudo journalctl -u beauty-booking-bot -f
```

Остановка:

```bash
sudo systemctl stop beauty-booking-bot
```

Запуск:

```bash
sudo systemctl start beauty-booking-bot
```

## Важно про сайт

Я не связывал жизненный цикл сайта и бота одним процессом. Это правильнее для VPS:
если бот перезапускается, nginx и сайт продолжают работать; если nginx перезагружается, бот продолжает работать.

Папка `api/` в исходном LUMI NAILS — это Vercel Functions. На обычном статическом nginx она сама по себе не исполняется как серверный API. Это отдельный вопрос от запуска Telegram-бота.
