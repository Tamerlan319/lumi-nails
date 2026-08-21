#!/usr/bin/env bash
set -u
echo "Проверка Telegram API:"
curl -4 -I --connect-timeout 10 https://api.telegram.org/ || true
echo
echo "TCP 443:"
timeout 5 bash -c '</dev/tcp/api.telegram.org/443' && echo "OK: порт 443 доступен" || echo "FAIL: порт 443 недоступен"
