#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
FULL='happ-tmn/happ-tmn-subscriptions'
[ -s sources.private.txt ] || { echo 'Источники пустые: sources.private.txt'; exit 1; }
[ "$(gh api user --jq .login)" = 'happ-tmn' ] || { echo 'Войди в аккаунт happ-tmn с помощью gh auth switch'; exit 1; }
if ! gh repo view "$FULL" >/dev/null 2>&1; then echo 'Сначала выполни deploy.sh'; exit 1; fi
gh secret set SOURCES_TXT -R "$FULL" < sources.private.txt
echo 'Секрет источников обновлён (значения не раскрываются).'
gh workflow run refresh.yml -R "$FULL"
echo 'Обновление запущено. Проверь вкладку Actions.'
