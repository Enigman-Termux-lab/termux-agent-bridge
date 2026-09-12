# 🚀 Termux Agent Gateway (MCP)

Универсальный, открытый и безопасный шлюз по протоколу **Model Context Protocol (MCP)**, превращающий смартфон на **Android / Termux** в мощную управляемую среду для любых современных ИИ-агентов:
* **OpenAI Codex**
* **Claude Code (Anthropic)**
* **Google Antigravity & Gemini CLI**
* **Gemini Spark (Connected Apps)**
* **Cursor & Windsurf IDE**

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
                    [ Termux Agent Gateway (Python / FastMCP) ]
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

---

## 🛡️ Матрица профилей безопасности

| Профиль | Риск | Инструменты в MCP | Описание и защита |
| :--- | :---: | :--- | :--- |
| **🟢 1. MONITOR** | 0 / 5 | `system_status`, `battery_info`, `tail_log` | **Только чтение.** Доступ к bash и модификации файлов полностью вырезан из схемы MCP. |
| **🟡 2. WORKSPACE** | 2 / 5 | `system_status`, `battery_info`, `tail_log`, `workspace_bash`, `file_read`, `file_write` | **Изолированная песочница.** Команды и файлы строго ограничены каталогом `~/workspace`. Запрещен переход вверх (`..`), запрещен `pkg`, запрещен доступ к `/data` и `/sdcard`. |
| **🟠 3. INTERACTIVE** *(Рекомендуется)* | 1.5 / 5 | `system_status`, `battery_info`, `tail_log`, `bash_run` | **Контроль в реальном времени.** Безопасные команды (`ls`, `cat`, `git status`) исполняются мгновенно. Опасные команды вызывают push-уведомление с кнопками в Android (таймаут 45 сек). |
| **🔴 4. GODMODE** | 5 / 5 | `system_status`, `battery_info`, `tail_log`, `bash_run`, `antigravity_run`, `termux_api` | **Полный доступ.** Неограниченный шелл, вызов локального автономного агента Antigravity CLI (`agy`), управление железом через Termux:API. |

---

## ⚡ Быстрый старт на телефоне (Termux)

### 1. Клонирование и первичный запуск
Запустите в Termux одну команду:
```bash
git clone https://github.com/Enigman-Termux-lab/termux-agent-gateway.git ~/termux-agent-gateway
cd ~/termux-agent-gateway
chmod +x gateway.sh SparkMCP.sh
./gateway.sh
```

При первом запуске мастер настройки:
- Проверит `python`, `termux-api`, `ngrok`, библиотеки `mcp`, `starlette`, `uvicorn`.
- Запросит ваш домен ngrok (например, `unstaffed-clamshell-overplant.ngrok-free.dev`).
- Предложит выбрать профиль безопасности (по умолчанию: `3 - INTERACTIVE`).
- Сгенерирует стойкий секретный Capability-путь.
- Запустит сервер и автоматически скопирует готовый URL в буфер обмена Android!

### 2. Управление шлюзом
```bash
./gateway.sh run       # Запуск шлюза и туннеля ngrok
./gateway.sh stop      # Остановка всех процессов
./gateway.sh restart   # Перезапуск
./gateway.sh status    # Текущий статус процессов
./gateway.sh copy      # Повторно скопировать URL в буфер
./gateway.sh config    # Запустить мастер настройки повторно
```

---

## 🔌 Подключение к ИИ-агентам

### 1. OpenAI Codex
1. В интерфейсе Codex откройте: **Settings** → **MCP servers** → **Add server**.
2. Заполните параметры:
   - **Name:** `Termux MCP Bridge`
   - **Type:** `Streamable HTTP`
   - **URL:** Полный адрес из Termux, например:  
     `https://unstaffed-clamshell-overplant.ngrok-free.dev/spark-7e4a19b8c0d3e5f2a1b4c6d8/sse`
   - **Authentication:** `None`
3. Нажмите **Save** и перезапустите Codex.
4. Проверьте работоспособность запросом к агенту:
   > *«Проверь Termux через system_status»*

> [!WARNING]
> **Важно:** Токен ngrok (`rd_...`) добавлять в Codex категорически нельзя! Токен авторизуется исключительно локально на телефоне в файле `~/.config/ngrok/ngrok.yml`.

---

### 2. Claude Code
Добавьте сервер одной командой:
```bash
claude mcp add termux --transport http https://<NGROK_DOMAIN>/<SECRET_PATH>/sse
```

---

### 3. Google Antigravity & Gemini CLI
В конфигурационном файле MCP (`mcp_config.json`):
```json
{
  "mcpServers": {
    "termux": {
      "url": "https://<NGROK_DOMAIN>/<SECRET_PATH>/sse"
    }
  }
}
```

---

### 4. Gemini Spark
1. Откройте **Settings** → **Connected Apps** → **Custom apps for Spark**.
2. Укажите URL: `https://<NGROK_DOMAIN>/<SECRET_PATH>/sse`.
3. Тип аутентификации: **None**.

---

## 🔔 Push-подтверждение в Android (Termux:API)

> [!IMPORTANT]
> Для работы подтверждений требуется отдельное приложение **[Termux:API](https://github.com/termux/termux-api/releases)** (F-Droid) с разрешением на уведомления и пакет `pkg install termux-api`.

В режиме **INTERACTIVE** опасные команды (`rm`, `pkg`, `kill`, `chmod`) не выполняются вслепую:
1. На телефон приходит push-уведомление с кнопками **«Разрешить»** и **«Заблокировать»**.
2. По клику «Разрешить» — команда выполняется агентом.
3. По клику «Заблокировать» (или таймауту 45с) — отклоняется с возвратом ошибки.

---

## 📁 Структура репозитория

```text
termux-agent-bridge/
├── gateway.py                # Ядро сервера (Starlette + MCP SDK + 4 профиля безопасности)
├── gateway.sh                # Умный лаунчер с выбором 4 режимов и ярлыком виджета
├── bridge.py                 # Нейтральный сервер-мост (Streamable HTTP / SSE)
├── approval_daemon.py        # Модуль валидации команд и push-уведомлений Android
├── config.example.env        # Шаблон конфигурации (~/.termux_agent_gateway.env)
├── agy_bridge.py             # Псевдоним обратной совместимости (ссылается на bridge.py)
├── skills/
│   └── termux-agent-gateway/ # Готовый универсальный MCP-скилл для агентов
└── README.md                 # Данная документация
```

---

## ⚙️ Устранение неполадок (FAQ)

### 1. `ngrok` не резолвит DNS в Android
В некоторых версиях Android Termux использует нестандартный DNS resolver. Для запуска ngrok используется утилита `termux-chroot`:
```bash
termux-chroot ngrok http 8000 --url="<NGROK_DOMAIN>"
```
Скрипт `gateway.sh` определяет наличие `termux-chroot` автоматически.

### 2. Не приходят уведомления `termux-notification`
- Убедитесь, что установлено приложение **Termux:API** из F-Droid.
- Откройте системные настройки Android → Приложения → **Termux:API** → Разрешения → включите «Уведомления».
- Отключите оптимизацию батареи для Termux и Termux:API.

### 3. Смена скомпрометированного секретного пути
Если ваш URL попал в публичный чат:
1. Отредактируйте `~/.termux_agent_gateway.env` (или запустите `./gateway.sh config`).
2. Поместите старый путь в `OLD_SECRET_PATH`, а новый сгенерируйте в `SECRET_PATH`.
3. Перезапустите шлюз: `./gateway.sh restart`.

---

## 📄 Лицензия

MIT License. Сделано для свободного взаимодействия ИИ-агентов с мобильным миром Android.
