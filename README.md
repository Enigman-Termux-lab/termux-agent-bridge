# 🚀 Termux Agent Bridge (MCP) v2.0
> **Управляй смартфоном Android прямо из любимых ИИ-агентов на ПК через протокол Model Context Protocol!**

<p align="center">
  <img src="https://img.shields.io/badge/Release-v2.0.0-success?style=for-the-badge&logo=github" alt="Release v2.0.0">
  <img src="https://img.shields.io/badge/Protocol-MCP%202026-blue?style=for-the-badge&logo=fastapi" alt="MCP">
  <img src="https://img.shields.io/badge/Platform-Android%20Termux-brightgreen?style=for-the-badge&logo=android" alt="Android Termux">
  <img src="https://img.shields.io/badge/Control-PC%20%E2%9E%A1%EF%B8%8F%20Android-orange?style=for-the-badge&logo=powershell" alt="PC to Android">
  <img src="https://img.shields.io/badge/Security-2--Level%20Auth-red?style=for-the-badge&logo=shield" alt="Security">
</p>

```text
 💻 DESKTOP PC / CLOUD AI                🌐 GLOBAL INTERNET                  📱 ANDROID / TERMUX
 ╔═════════════════════════╗            ╔═════════════════════════╗           ╔═════════════════════════╗
 ║   🧠 OpenAI Codex       ║            ║                         ║           ║   🤖 FastMCP Gateway    ║
 ║   ⚡ Claude Code (CLI)  ║───────────►║    Ngrok SSE Tunnel     ║──────────►║   💻 Bash / Python / agy║
 ║   🚀 Google Antigravity ║  MCP JSON  ║   (*.ngrok-free.dev)    ║  Encrypted║   🔋 Battery & Sensors  ║
 ║   ✨ Gemini Spark       ║    RPC     ║                         ║Capability ║   🔔 Android Push Alerts║
 ╚═════════════════════════╝            ╚═════════════════════════╝           ╚═════════════════════════╝
            │                                                                              │
            └───────────────────────── Прямой удаленный контроль ─────────────────────────┘
```

Универсальный, открытый и безопасный шлюз по протоколу **Model Context Protocol (MCP)**, превращающий смартфон на **Android / Termux** в мощную управляемую среду для любых современных ИИ-агентов.

---

## 🎯 Архитектура и возможности

```text
  [ OpenAI Codex ]     [ Claude Code ]     [ Google Antigravity ]     [ Gemini Spark ]
          │                   │                      │                       │
          └───────────────────┴──────────┬───────────┴───────────────────────┘
                                         │ Streamable HTTP / SSE
                                         ▼
                      [ Ngrok Tunnel (*.ngrok-free.dev) ]
                                         │
                                         ▼ (Secret Capability Path)
                    [ Termux Agent Bridge (Python / FastMCP) ]
                                         │
        ┌───────────────────┬────────────┴───────┬───────────────────┐
        ▼                   ▼                    ▼                   ▼
    🟢 MONITOR          🟡 WORKSPACE        🟠 INTERACTIVE      🔴 GODMODE
   (Только чтение:     (Песочница:         (Push-уведомление   (Полный root/
    статус, батарея,    команды строго      в Android с         bash доступ
    логи файлов)        в ~/workspace)      кнопками Да/Нет)    + agy CLI)
```

1. **Единый стандарт (Streamable HTTP / SSE):** Работает из коробки со всеми клиентами протокола MCP 2024–2026.
2. **4 динамических профиля безопасности:** Сервер экспортирует в схему MCP только разрешенные инструменты — агент физически не может вызвать недопустимую функцию.
3. **Интерактивное подтверждение в Android (Android Push Approval):** Опасные команды (`rm`, `mv`, `pkg`, `kill`, `curl`, `chmod`) автоматически приостанавливаются; на экране телефона появляется push-уведомление с кнопками «Разрешить» и «Заблокировать».
4. **Мастер настройки Zero-to-Hero (`gateway.sh`):** Быстрый интерактивный мастер на телефоне сам проверит зависимости, настроит ngrok, сгенерирует криптографический секрет и скопирует ссылку в буфер обмена.
5. **Экстремальный минимализм:** Все компоненты объединены всего в 4 ключевых файла без лишних зависимостей.

---

## 🛡️ Матрица профилей безопасности

| Профиль | Риск | Инструменты в MCP | Описание и защита |
| :--- | :---: | :--- | :--- |
| **🟢 1. MONITOR** | 0 / 5 | `system_status`, `battery_info`, `tail_log` | **Только чтение.** Доступ к bash и модификации файлов полностью вырезан из схемы MCP. |
| **🟡 2. WORKSPACE** | 2 / 5 | `system_status`, `battery_info`, `tail_log`, `workspace_bash`, `file_read`, `file_write` | **Изолированная песочница.** Команды и файлы строго ограничены каталогом `~/workspace`. Запрещен переход вверх (`..`), запрещен `pkg`, запрещен доступ к `/data` и `/sdcard`. |
| **🟠 3. INTERACTIVE** *(Рекомендуется)* | 1.5 / 5 | `system_status`, `battery_info`, `tail_log`, `bash_run` | **Контроль в реальном времени.** Безопасные команды (`ls`, `cat`, `git status`) исполняются мгновенно. Опасные команды вызывают push-уведомление с кнопками в Android (таймаут 45 сек). |
| **🔴 4. GODMODE** | 5 / 5 | `system_status`, `battery_info`, `tail_log`, `bash_run`, `antigravity_run`, `termux_api` | **Полный доступ.** Неограниченный шелл, вызов локального автономного агента Antigravity CLI (`agy`), управление железом через Termux:API. |

---

## 🛠️ Справочник инструментов (Tools Reference)

### Общие инструменты (все профили):
* `system_status()`: Сводка о системе (активный профиль, платформа, память, путь к workspace, наличие `agy` и `termux-api`).
* `battery_info()`: Состояние аккумулятора смартфона (уровень заряда %, температура, статус питания, состояние батареи).
* `tail_log(path, lines=50)`: Безопасное чтение последних N строк лог-файла (блокирует доступ к SSH-ключам и `.env`).

### Инструменты режима WORKSPACE:
* `workspace_bash(command)`: Выполнение bash-команд строго внутри изолированного каталога `~/workspace`. Блокирует попытки выхода из каталога и вызовы менеджеров пакетов.
* `file_read(path, offset=0, limit=8000)`: Чтение файлов внутри каталога `~/workspace`.
* `file_write(path, content, append=False)`: Запись или дополнение файлов внутри каталога `~/workspace`.

### Инструменты режимов INTERACTIVE и GODMODE:
* `bash_run(command, cwd=None)`: Выполнение bash-команд в Termux.  
  *В режиме INTERACTIVE:* Если команда содержит `rm`, `mv`, `pkg`, `kill`, `curl`, `chmod`, `git push --force` и т.д., выполнение приостанавливается до 45 секунд, пока пользователь не нажмет «Разрешить» в push-уведомлении на телефоне.  
  *В режиме GODMODE:* Выполняется мгновенно без запроса подтверждений.
* `antigravity_run(prompt, continue_session=True)`: *(Только GODMODE)* Запуск автономного локального кодинг-агента Antigravity CLI (`agy`) на устройстве.
* `termux_api(api_command, args=[])`: *(Только GODMODE)* Прямой вызов утилит Android API (`termux-toast`, `termux-vibrate`, `termux-clipboard-set`).

---

## 📋 Что нужно сделать ПЕРЕД подключением (Prerequisites)

Перед тем как подключить шлюз к вашему ИИ-агенту, выполните 2 простых подготовительных шага:

### Шаг 1. Бесплатная регистрация на Ngrok (1 раз)
1. Зарегистрируйтесь на сайте [dashboard.ngrok.com](https://dashboard.ngrok.com) (это бесплатно).
2. Перейдите в раздел [Your Authtoken](https://dashboard.ngrok.com/get-started/your-authtoken) и скопируйте ваш токен.
3. В разделе [Cloud Edge → Domains](https://dashboard.ngrok.com/cloud-edge/domains) нажмите **Create Domain** и получите постоянный бесплатный статический домен (например, `your-domain.ngrok-free.dev`), чтобы ссылка не менялась при перезапусках.

### Шаг 2. Действия на телефоне (Android / Termux)
1. Установите **[Termux из F-Droid](https://f-droid.org/packages/com.termux/)** *(версия из Google Play устарела и не работает)*.
2. *(Опционально)* Для подтверждения опасных команд кнопками на экране установите **[Termux:API из F-Droid](https://f-droid.org/packages/com.termux.api/)** и разрешите ему показ уведомлений в настройках Android.
3. Откройте Termux на телефоне и запустите мастер установки:
```bash
pkg update -y && pkg install -y git
git clone https://github.com/Enigman-Termux-lab/termux-agent-bridge.git ~/termux-agent-bridge
cd ~/termux-agent-bridge
chmod +x gateway.sh
./gateway.sh
```
4. Мастер настройки на экране телефона:
   - Проверит и установит недостающие пакеты;
   - Попросит вставить ваш Ngrok Token и статический домен;
   - Предложит выбрать режим безопасности (по умолчанию: `3 - INTERACTIVE`);
   - Сам сгенерирует секретный ключ, запустит сервер и **автоматически скопирует готовую ссылку в буфер обмена Android**!

### Управление шлюзом на телефоне
```bash
./gateway.sh run       # Запуск шлюза и туннеля ngrok
./gateway.sh stop      # Остановка всех процессов
./gateway.sh restart   # Перезапуск
./gateway.sh status    # Текущий статус процессов
./gateway.sh copy      # Скопировать URL в буфер обмена Android
./gateway.sh config    # Запустить мастер настройки повторно
```

---

## 🔌 Подключение к любому ИИ-агенту (Обычный протокол MCP)

Шлюз работает по **стандартному открытому протоколу MCP (Streamable HTTP / SSE)**. Для подключения не требуются сторонние надстройки или сложный OAuth2:

| Параметр в настройках MCP | Значение |
| :--- | :--- |
| **Тип транспорта (Type / Transport)** | `Streamable HTTP` (или `SSE` / `http`) |
| **URL сервера** | Ссылка из буфера обмена телефона (`https://<your-domain>.ngrok-free.dev/<SECRET_PATH>/sse`) |
| **Авторизация (Authentication)** | `None` (защита встроена в секретный capability-путь URL) |

### Примеры для популярных клиентов:
* **OpenAI Codex:** *Settings → MCP servers → Add server* → Type: `Streamable HTTP`, URL: ваша ссылка, Auth: `None`.
* **Claude Code CLI:** `claude mcp add termux --transport http https://<your-domain>.ngrok-free.dev/<SECRET_PATH>/sse`
* **Google Antigravity & IDE:** Добавьте в `mcp_config.json`: `{"termux": {"url": "https://<your-domain>.ngrok-free.dev/<SECRET_PATH>/sse"}}`
* **Gemini Spark:** *Settings → Connected Apps → Custom apps for Spark* → URL: ваша ссылка, Auth: `None`.
* **Cursor / Windsurf:** Укажите как SSE-сервер в `.cursor/mcp.json` без заголовков авторизации.

> [!WARNING]
> **Никогда не вводите токен ngrok в настройки MCP на компьютере!** Токен ngrok должен находиться исключительно на телефоне. Клиентам передается только итоговый URL с секретным capability-путем.

---

## 💡 Регламент работы для ИИ-агентов (Agent Guidelines)

1. **Архитектура окружения:** Вы работаете со смартфоном на Android (архитектура ARM64, Bionic libc, Termux). Системные бинарные файлы и утилиты расположены в `/data/data/com.termux/files/usr/bin`.
2. **Ожидание при подтверждении:** В режиме `INTERACTIVE` опасная команда приостанавливается до 45 секунд. В этот момент пользователю приходит push-уведомление на экран телефона. Не прерывайте операцию и не дублируйте вызов команды.
3. **Безопасные команды в приоритете:** Для инспекции и чтения используйте `cat`, `head`, `tail`, `ls`, `grep`, `git status` — они выполняются мгновенно без запроса подтверждения.
4. **Конфиденциальность секретов:** Файл конфигурации `~/.termux_agent_gateway.env` содержит секретные Capability-токены. Запрещено выводить или передавать его содержимое во внешние сервисы.

---

## 🔔 Push-подтверждение в Android (Termux:API)

> [!IMPORTANT]
> Для работы интерактивных подтверждений требуется отдельное приложение **[Termux:API](https://github.com/termux/termux-api/releases)** (F-Droid) с разрешением на отправку уведомлений и установленный пакет `pkg install termux-api`.

В режиме **INTERACTIVE** потенциально деструктивные операции (`rm`, `pkg`, `kill`, `chmod`, перенаправления в системные каталоги) не исполняются вслепую:
1. На телефон мгновенно приходит push-уведомление с кнопками **«Разрешить»** и **«Заблокировать»** и вибросигналом.
2. По нажатию «Разрешить» — команда успешно выполняется агентом.
3. По нажатию «Заблокировать» (или по истечении 45 секунд) — команда блокируется с сообщением об отклонении.

---

## 📁 Структура репозитория (Консолидированная)

```text
termux-agent-bridge/
├── gateway.py          # Ядро сервера (FastMCP + Starlette, 4 профиля безопасности, валидатор и push-демон)
├── gateway.sh          # Единый CLI-скрипт (Zero-to-Hero мастер настройки, запуск, статус, остановка)
├── config.example.env  # Шаблон конфигурации (~/.termux_agent_gateway.env)
├── README.md           # Документация, справочник инструментов и регламент для ИИ-агентов
└── .gitignore          # Исключение секретов, виртуальных окружений и логов
```

---

## ⚙️ Устранение неполадок (FAQ)

### 1. `ngrok` не резолвит DNS в Android
В некоторых версиях Android Termux использует нестандартный DNS resolver. Для корректной работы ngrok скрипт `gateway.sh` автоматически использует `termux-chroot`:
```bash
termux-chroot ngrok http 8000 --url="<your-domain>.ngrok-free.dev"
```

### 2. Не приходят уведомления `termux-notification`
- Убедитесь, что установлено приложение **Termux:API** из F-Droid.
- Откройте системные настройки Android → Приложения → **Termux:API** → Разрешения → включите «Уведомления».
- Отключите оптимизацию батареи для Termux и Termux:API.

### 3. Смена скомпрометированного секретного пути
Если ваш URL случайно попал в открытый доступ:
1. Отредактируйте `~/.termux_agent_gateway.env` (или запустите `./gateway.sh config`).
2. Поместите скомпрометированный путь в `OLD_SECRET_PATH`, а новый ключ сгенерируйте в `SECRET_PATH`.
3. Перезапустите шлюз: `./gateway.sh restart`.

---

## 📄 Лицензия

MIT License. Сделано для свободного взаимодействия ИИ-агентов с мобильным миром Android.
