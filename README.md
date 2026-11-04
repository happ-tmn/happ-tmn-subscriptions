# @happ_tmn · Subscription Collector

Автоматический сборщик общедоступных VPN-конфигураций: GitHub Actions запускает обновление каждые 3 часа и публикует **обычные TXT** (без внешней Base64-кодировки). Владелец репозитория может запустить обновление вручную.

## Подписки

Замените `<OWNER>` на `happ-tmn`, а `<REPO>` на `happ-tmn-subscriptions`. Формат:

`https://raw.githubusercontent.com/<OWNER>/<REPO>/main/sub/all.txt`

- `sub/all.txt` — все поддерживаемые конфигурации
- `sub/vless.txt`, `sub/vmess.txt`, `sub/trojan.txt`, `sub/ss.txt`, `sub/ssr.txt`, `sub/hysteria2.txt`, `sub/tuic.txt`
- `sub/tls.txt`, `sub/reality.txt`, `sub/ws.txt`, `sub/xhttp.txt`, `sub/grpc.txt`, `sub/tcp.txt`, `sub/httpupgrade.txt`, `sub/h2.txt`, `sub/none.txt`
- `sub/vless/tls/ws.txt`, `sub/vless/reality.txt`, **`sub/vless/reality-vision.txt`**, `sub/vless/xhttp.txt`
- `sub/trojan/tls.txt`, `sub/vmess/tls/ws.txt`
- `sub/pages/all-001.txt`, `all-002.txt` и далее — части большой подписки
- `status.json` — суммарные счётчики обновления; **адресов источников в статусе нет**

Reality Vision отбирается строго по сочетанию `security=reality` **и** `flow=xtls-rprx-vision`. Весь query string включая `flow`, `sni`, `pbk`, `sid`, `fp`, `host`, `path`, нестандартные порты и прочее сохраняется **байт-в-байт** для URL-конфигов: меняется только имя после `#`. VMess сохраняет все JSON-поля, меняя только `ps`. SSR сохраняет параметры, меняя лишь `remarks`. Оригинальные эмодзи-флаги стран входят в новое название вида `🇸🇬 @happ_tmn a1b2c3`.

## Первый запуск (Termux)

1. Распакуйте скачанный ZIP **в папку Downloads**. В нём `sources.private.txt` — приватный локальный список доноров.
2. Установите `git`, `gh`, `python`: `pkg install git gh python -y`.
3. Авторизуйтесь в `gh` как **happ-tmn** (не другой GitHub-аккаунт): `gh auth login --hostname github.com --git-protocol https --web` и при необходимости `gh auth switch --hostname github.com --user happ-tmn`.
4. В Termux перейдите в извлечённую папку и выполните `bash deploy.sh`. Скрипт создаст **публичный** репозиторий `happ-tmn/happ-tmn-subscriptions`, загрузит в него код **без файла доноров**, сохранит URL-источники в **Actions Secret `SOURCES_TXT`** и вручную запустит первое обновление.
5. Откройте вкладку Actions нового репозитория и проверьте успешность запуска. Только после этого импортируйте подписку в Nekobox. Если Actions отклоняет отправку с `403`, проверьте **Settings → Actions → General → Workflow permissions → Read and write permissions**.

⚠️ Не загружайте `sources.private.txt` через интерфейс GitHub вручную, даже в историю коммитов. Список скрыт от посетителей, но **не от самой платформы GitHub**. Конфигурации могут раскрывать хосты косвенно. Публичный код и сгенерированные конфиги также видны GitHub. Скрипт не делает реальных сетевых тестов прокси; выдача URL не гарантирует работоспособность узла.

## Изменение источников

В Termux откройте локальный `sources.private.txt` и замените строки (по одному HTTPS URL на строку). Затем:

```bash
cd ~/storage/downloads/happ_tmn_subscriptions
bash update_sources.sh
```

Скрипт обновит секрет `SOURCES_TXT` и запросит новый запуск workflow. **Публичный репозиторий от этих действий не получит файл с донорскими ссылками.** При ошибке загрузки одного из источников прежний опубликованный снимок не заменяется неполным (если он уже был).

## Полезное

- Ручной запуск в Termux: `gh workflow run refresh.yml -R happ-tmn/happ-tmn-subscriptions`
- Мониторинг: `gh run list -R happ-tmn/happ-tmn-subscriptions --limit 5`
- Скачать актуальную TXT-подписку: `https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/all.txt`
- Протоколы: VLESS / VMess / Trojan / SS / SSR / Hysteria2 / TUIC; дополнительно парсятся SOCKS и HTTP с явным портом (в группе `all`).
- Некоторые клиенты Nekobox не поддерживают всякий тип конфигураций — используйте специализированную подписку.

## Ограничения

Это сборщик ссылок, **не сервер** VLESS/Reality. Он не создаёт новые узлы, а группирует конфигурации из указанных источников, без проверки подключения. Используйте источники с разрешённой перепубликацией и соблюдайте условия GitHub и поставщиков данных. Плановое задание Actions может задержаться; ручной запуск предусмотрен.
