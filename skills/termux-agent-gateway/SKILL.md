---
name: termux-agent-gateway
description: Универсальный MCP-шлюз для удалённого управления Android Termux из любых ИИ-агентов (OpenAI Codex, Claude Code, Google Antigravity, Gemini Spark, Cursor, Windsurf).
---

# 🚀 Termux Agent Gateway: Инструкция для ИИ-агентов

Универсальный шлюз по протоколу **Model Context Protocol (MCP)**, позволяющий ИИ-агентам безопасно взаимодействовать с окружением Android / Termux на смартфоне.

---

## 🔌 Конфигурация подключения для популярных агентов

### 1. OpenAI Codex
В графическом интерфейсе Codex:
1. Откройте: **Settings** → **MCP servers** → **Add server**
2. Заполните поля:
   - **Name:** `Termux MCP Bridge`
   - **Type:** `Streamable HTTP`
   - **URL:** `https://<NGROK_DOMAIN>/<SECRET_PATH>/sse`
     *(Пример: `https://unstaffed-clamshell-overplant.ngrok-free.dev/spark-7e4a19b8c0d3e5f2a1b4c6d8/sse`)*
   - **Authentication:** `None`
3. Нажмите **Save** и перезапустите Codex.
4. Проверьте статус подключения командой:
   > *«Проверь Termux через system_status»*

> [!CAUTION]
> **Ни в коем случае не вводите токен ngrok (`rd_...`) в настройки Codex!**  
> Токен ngrok должен находиться исключительно на телефоне в Termux (`~/.config/ngrok/ngrok.yml`).

---

### 2. Claude Code (Anthropic CLI)
Подключение через терминал одной командой:
```bash
claude mcp add termux --transport http https://<NGROK_DOMAIN>/<SECRET_PATH>/sse
```

Или добавлением в `~/.claude.json`:
```json
{
  "mcpServers": {
    "termux": {
      "url": "https://<NGROK_DOMAIN>/<SECRET_PATH>/sse",
      "transport": "http"
    }
  }
}
```

---

### 3. Google Antigravity & Gemini CLI
Конфигурация в настройках MCP (`~/.gemini/antigravity/mcp_config.json` или sidecar):
```json
{
  "mcpServers": {
    "termux-gateway": {
      "url": "https://<NGROK_DOMAIN>/<SECRET_PATH>/sse"
    }
  }
}
```

---

### 4. Gemini Spark (Web / Mobile App)
1. В интерфейсе Gemini Spark откройте: **Settings** → **Connected Apps** → **Custom apps for Spark**.
2. Введите URL: `https://<NGROK_DOMAIN>/<SECRET_PATH>/sse`.
3. Установите тип авторизации: **Authentication: None**.
4. Сохраните.

---

## 🛡️ Профили безопасности (Security Profiles)

Шлюз динамически объявляет только те инструменты, которые разрешены текущим профилем на телефоне:

| Профиль | Риск | Доступные инструменты | Описание |
| :--- | :---: | :--- | :--- |
| **🟢 MONITOR** | 0 / 5 | `system_status`, `battery_info`, `tail_log` | Только чтение. Вызов bash и запись файлов физически заблокированы. |
| **🟡 WORKSPACE** | 2 / 5 | `system_status`, `battery_info`, `tail_log`, `workspace_bash`, `file_read`, `file_write` | Жесткая песочница в `~/workspace`. Запрещены `..`, `pkg`, системные каталоги. |
| **🟠 INTERACTIVE** *(Рекомендуется)* | 1.5 / 5 | `system_status`, `battery_info`, `tail_log`, `bash_run` | Безопасные команды работают сразу. Опасные команды требуют клика «Разрешить» в Android push-уведомлении. |
| **🔴 GODMODE** | 5 / 5 | `system_status`, `battery_info`, `tail_log`, `bash_run`, `antigravity_run`, `termux_api` | Полный неограниченный доступ ко всем командам Termux, Antigravity CLI и Termux:API. |

---

## 🛠️ Справочник инструментов (Tools Reference)

### Общие инструменты (все профили):
- `system_status()`: Возвращает отчет о состоянии системы (активный профиль, память, путь к workspace, наличие `agy` и `termux-api`).
- `battery_info()`: Возвращает уровень заряда батареи смартфона, температуру, статус питания и состояние аккумулятора.
- `tail_log(path, lines=50)`: Читает последние N строк лог-файла.

### Инструменты WORKSPACE:
- `workspace_bash(command)`: Выполняет команду внутри изолированного каталога `~/workspace`. Блокирует попытки выхода из каталога и вызовы менеджеров пакетов.
- `file_read(path, offset=0, limit=8000)`: Читает текстовый файл внутри `~/workspace`.
- `file_write(path, content, append=False)`: Записывает или дополняет файл внутри `~/workspace`.

### Инструменты INTERACTIVE и GODMODE:
- `bash_run(command, cwd=None)`: Выполняет bash-команду в Termux.  
  *В режиме INTERACTIVE:* Если команда содержит `rm`, `mv`, `pkg`, `kill`, `curl`, `chmod`, `git push --force` и т.д., сервер приостанавливает выполнение до 45 секунд, пока пользователь не нажмет кнопку «Разрешить» в push-уведомлении Android.
- `antigravity_run(prompt, continue_session=True)`: Запускает локального автономного кодинг-агента Antigravity CLI (`agy`) на устройстве.
- `termux_api(api_command, args=[])`: Прямой вызов утилит Android API (`termux-toast`, `termux-vibrate`, `termux-clipboard-set`).

---

## 💡 Регламент работы для ИИ-агентов

1. **Не путайте окружения:** Вы работаете со смартфоном на Android (архитектура ARM64, Bionic libc, Termux). Пути к утилитам обычно находятся в `/data/data/com.termux/files/usr/bin`.
2. **Терпение при подтверждении:** В режиме `INTERACTIVE` опасная команда может выполняться до 45 секунд. Это нормальный процесс — пользователь подтверждает действие на экране смартфона. Не дублируйте запрос повторно.
3. **Предпочитайте безопасные команды:** Для чтения используйте `cat`, `head`, `tail`, `ls`, `grep` — они исполняются мгновенно без запроса подтверждения.
4. **Конфиденциальность:** Файл конфигурации `~/.termux_agent_gateway.env` содержит секретные ключи. Никогда не читайте и не отправляйте его содержимое в сторонние сервисы.
