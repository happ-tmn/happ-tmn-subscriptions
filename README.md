<p align="center">
  <img src="assets/yinglong_banner.png" alt="Happ TMN — крылатый дракон Инлун, сборщик VPN-подписок" width="100%">
</p>

<h1 align="center">🐉 Happ TMN — подписки для Nekobox</h1>

<p align="center">
  <b>VLESS · VMess · Trojan · Shadowsocks · SSR · Hysteria2 · TUIC</b><br>
  Автоматическое обновление · обычный TXT · отдельная Reality Vision
</p>

<p align="center">
  <a href="https://t.me/happ_tmn"><b>💙 Подпишись на наш Telegram-канал @happ_tmn</b></a>
</p>

---

## ✨ О проекте

**Happ TMN Subscriptions** собирает общедоступные конфигурации из нескольких источников, убирает дубликаты, сортирует по протоколам и публикует удобные **TXT-подписки** для Nekobox, v2rayNG и совместимых клиентов.

- 🔄 **Обновление каждые 3 часа** через GitHub Actions (cron `17 */3 * * *`, UTC).
- 🏷️ **Единый стиль:** имена конфигураций превращаются в `🇸🇬 @happ_tmn a1b2c3` с сохранением исходных эмодзи-флагов.
- 🔐 **Все параметры подключения сохраняются:** UUID, IP, порт, `flow`, `sni`, `pbk`, `sid`, `fp`, `host`, `path`, `security`, `type` и другие поля. У URL-ссылок меняется только часть после `#`; у VMess — только поле `ps`; у SSR — только `remarks`.
- 💎 **Отдельная подписка VLESS Reality Vision:** только узлы с `security=reality` и `flow=xtls-rprx-vision`.
- 📄 **Никакого Base64-оборачивания всей страницы:** каждая ссылка выдаётся обычной строкой в `.txt`.

## 📥 Подписки

> Ссылки начнут отдавать данные **после первого успешного запуска** GitHub Actions. Пустая выборка означает, что у источников не нашлось конфигураций нужного типа.

| Подписка | TXT |
|:--|:--|
| 🌐 **Все конфигурации** | [sub/all.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/all.txt) |
| 💎 **VLESS Reality Vision** | [sub/vless/reality-vision.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/vless/reality-vision.txt) |
| 🔐 VLESS Reality | [sub/vless/reality.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/vless/reality.txt) |
| ⚡ VLESS | [sub/vless.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/vless.txt) |
| 📡 VMess | [sub/vmess.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/vmess.txt) |
| 🛡️ Trojan | [sub/trojan.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/trojan.txt) |
| 🌀 Shadowsocks | [sub/ss.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/ss.txt) |
| 🌊 SSR | [sub/ssr.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/ssr.txt) |
| 🚀 Hysteria2 | [sub/hysteria2.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/hysteria2.txt) |
| ✨ TUIC | [sub/tuic.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/tuic.txt) |
| 🔗 WebSocket | [sub/ws.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/ws.txt) |
| 📦 XHTTP | [sub/xhttp.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/xhttp.txt) |
| 🧩 gRPC | [sub/grpc.txt](https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/grpc.txt) |

Есть и другие фильтры: `tls`, `reality`, `none`, `tcp`, `httpupgrade`, `h2`, `vless/tls/ws`, `vless/xhttp`, `trojan/tls`, `vmess/tls/ws`. Если общая подписка слишком большая, она дополнительно разделяется на `sub/pages/all-001.txt`, `all-002.txt` и далее.

## 🫶 Наш Telegram

Новые конфигурации, новости и помощь с подключением — в нашем канале:

### 👉 [Подпишись на @happ_tmn](https://t.me/happ_tmn)

---

<details>
<summary><b>🛠️ Для администратора: установка через Termux</b></summary>

1. Распакуй архив проекта в `Downloads`. Не выкладывай архив целиком в публичный репозиторий: в нём есть локальный список доноров.
2. Убедись, что установлены `git`, `gh` и `python` (если зеркало Termux отвечает `429`, поменяй зеркало через `termux-change-repo`).
3. Авторизуй GitHub CLI именно под `happ-tmn`.
4. Из папки Downloads запускай:

```bash
cd ~/storage/downloads/happ_tmn_subscriptions
gh auth switch -h github.com -u happ-tmn
bash deploy.sh
```

`deploy.sh` сам использует **временную рабочую папку внутри Termux** для Git, поэтому запуск из Android Downloads безопасен. Он создаёт репозиторий `happ-tmn/happ-tmn-subscriptions` (если его нет), публикует код и баннер, добавляет список доноров в GitHub Actions Secret `SOURCES_TXT` и запускает обновление.

### Замена источников

Открой локальный `sources.private.txt` в Downloads и замени строки (по одному HTTPS-адресу на строку), затем выполни:

```bash
cd ~/storage/downloads/happ_tmn_subscriptions
bash update_sources.sh
```

Не публикуй `sources.private.txt` и токены в GitHub. Секреты Actions не видны обычным посетителям, но GitHub технически обрабатывает их во время выполнения.

### Управление обновлением

```bash
gh workflow run refresh.yml -R happ-tmn/happ-tmn-subscriptions
gh run list -R happ-tmn/happ-tmn-subscriptions --limit 5
```

Если Actions не может отправить результат (`403`), проверь **Settings → Actions → General → Workflow permissions → Read and write permissions**. В `status.json` публикуется статистика без исходных URL.

</details>

<details>
<summary><b>ℹ️ Ограничения и безопасность</b></summary>

Это **сборщик готовых конфигураций**, а не сервер VLESS/Reality. Он не создаёт новые узлы и **не проверяет реальное соединение** с каждым прокси. Работоспособность, срок жизни и доступность зависят от их владельцев. Некоторые клиенты не поддерживают все типы URI, поэтому предпочтительны специализированные подписки. Для источников соблюдай условия перепубликации и правила площадок.

</details>

<p align="center">
  <b>🐉 Happ TMN</b> · <a href="https://t.me/happ_tmn">Telegram: @happ_tmn</a>
</p>
