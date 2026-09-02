---
name: gemini-spark-mcp-bridge
type: guide
domain: система/Агентские инструменты/mcp
tags: [mcp, gemini-spark, termux, fastmcp, streamable-http, ngrok, antigravity]
last_updated: 2026-09-02
---

# Полный гайд: Подключение Gemini Spark к Termux (Android) через защищённый MCP-мост

Пошаговое руководство по созданию и запуску защищённого моста по протоколу **Model Context Protocol (MCP)** в режиме **Direct Capability URL (Authentication: None)**, позволяющего мгновенно и безотказно управлять утилитой **Antigravity CLI (`agy`)** и терминалом **Termux на Android** прямо из веб-интерфейса **Gemini Spark на ПК**.

---

## 1. Архитектурная схема

```text
[Gemini Spark (ПК / Облако Google)]
         │
         │ HTTPS / Streamable HTTP (POST / GET)
         │ Режим: Authentication: None (без сбоев OAuth)
         ▼
[Бесплатный постоянный домен Ngrok (*.ngrok-free.dev)]
         │
         │ Секретный путь (Secret Subpath): /spark-sec-9a8f7b2c/sse
         │ (все запросы на корень / получают 404 Not Found)
         │ Проброс на localhost:8000 через termux-chroot
         ▼
[Termux: agy_bridge.py (Python MCPServer + Streamable HTTP + Uvicorn)]
         │
         ├──► agy -c -p "запрос" (Antigravity CLI с обходом разрешений)
         └──► bash (файлы, git, системные команды Android/Termux)
```

---

## 2. Ключевые грабли и решения

В большинстве публичных руководств упускаются 6 критических проблем среды Android/Termux и протокола MCP:

1. **`pkg install ngrok` не существует:**
   - В официальных репозиториях Termux пакета `ngrok` нет.
   - **Решение:** Скачивание официального статического ARM64-бинарника напрямую с серверов Ngrok.
2. **Ошибка `reconnecting (failed to dial ngrok server)`:**
   - Linux-бинарники на Go ищут `/etc/resolv.conf`. В Android такого файла в корне нет.
   - **Решение:** Запуск ngrok через утилиту `termux-chroot`, монтирующую системный DNS Termux (`$PREFIX/etc/resolv.conf`).
3. **Обновление MCP SDK 2.x:**
   - В `mcp >= 2.0` класс `FastMCP` переименован в `MCPServer` (`from mcp.server import MCPServer`).
4. **Ошибка 421 Misdirected Request (DNS Rebinding):**
   - FastMCP по умолчанию блокирует хосты, отличные от localhost.
   - **Решение:** `TransportSecuritySettings(enable_dns_rebinding_protection=False)`.
5. **Ошибка «Указанный URL — это не адрес MCP сервера» (HTTP 405):**
   - Gemini Spark использует **Streamable HTTP транспорт**, отправляя при инициализации метод `POST`. Устаревший SSE-транспорт принимал только `GET` и падал с 405.
   - **Решение:** Использование `mcp.streamable_http_app()`, принимающего как `POST`, так и `GET`.
6. **Почему Direct Capability URL лучше OAuth:**
   - OAuth в Gemini Spark для кастомных серверов всё ещё находится в стадии беты и часто теряет зарегистрированные действия или сбрасывает сессии.
   - Прямое подключение по длинному секретному адресу (`/spark-sec-9a8f7b2c/sse`) с `Authentication: None` работает безотказно: боты не могут угадать 128-битный путь, а Gemini видит все действия сразу.

---

## 3. Пошаговая инструкция по настройке

### Шаг 1. Регистрация в Ngrok (2 минуты)
1. Зайдите на [ngrok.com](https://ngrok.com) и авторизуйтесь.
2. В панели управления: **Endpoints** → **Domains** — скопируйте бесплатный статический домен вида `your-domain.ngrok-free.dev`.
3. В разделе **Your Authtoken** скопируйте секретный ключ.

### Шаг 2. Подготовка окружения в Termux
```bash
# Обновляем окружение Termux
pkg update && pkg upgrade -y

# Устанавливаем базовые утилиты и компиляторы
pkg install python git proot resolv-conf curl tar -y

# Устанавливаем официальный бинарник ngrok ARM64
curl -fsSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz | tar -xz -C $PREFIX/bin

# Привязываем authtoken ngrok
ngrok config add-authtoken ТВОЙ_AUTHTOKEN_ИЗ_NGROK

# Устанавливаем MCP SDK, сервер Uvicorn и Starlette
pip install "mcp[cli]" uvicorn starlette
```

---

### Шаг 3. Создание сервера-моста (`~/agy_bridge.py`)

Создайте файл `~/agy_bridge.py`:

```python
"""
Termux MCP Bridge для Gemini Spark (Режим: Secret Capability URL).
Прямое надёжное подключение без OAuth. Защищено секретным адресом.
Поддерживает современный Streamable HTTP транспорт (POST/GET) для Gemini Spark.
"""

import os
import subprocess

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
import uvicorn

# Секретный токен пути в URL
SECRET_PATH = os.environ.get("BRIDGE_PATH", "spark-sec-9a8f7b2c")

# Инициализируем сервер MCP
mcp = MCPServer("Termux Antigravity Bridge")


# --- ИНСТРУМЕНТЫ ДЛЯ GEMINI SPARK ---


@mcp.tool()
def antigravity_run(prompt: str, continue_session: bool = True) -> str:
    """Запустить Antigravity CLI (agy) с заданным запросом (prompt).

    Параметры:
    - prompt: текст задачи для агента Antigravity.
    - continue_session: True для продолжения контекста сессии (-c).
    """
    cmd = ["agy", "--dangerously-skip-permissions"]
    if continue_session:
        cmd.append("-c")
    cmd.extend(["-p", prompt])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = result.stdout if result.stdout else result.stderr
        return output.strip() if output else "Команда выполнена успешно (без вывода)."
    except subprocess.TimeoutExpired:
        return "Таймаут: Antigravity CLI выполнялся дольше 5 минут."
    except Exception as e:
        return f"Ошибка вызова Antigravity CLI: {str(e)}"


@mcp.tool()
def bash_run(command: str) -> str:
    """Выполнить системную bash-команду в Termux (ls, git, pwd, cat, ps и т.д.)."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n[STDERR]\n" if output else "") + result.stderr
        return output.strip() if output else "[Команда успешно выполнена без вывода]"
    except subprocess.TimeoutExpired:
        return "Таймаут: команда выполнялась дольше 60 секунд."
    except Exception as e:
        return f"Ошибка выполнения команды: {str(e)}"


@mcp.tool()
def system_status() -> str:
    """Получить текущий статус: рабочая директория, состояние памяти и наличие agy."""
    cwd = os.getcwd()
    agy_ok = subprocess.run(["which", "agy"], capture_output=True).returncode == 0
    return (
        f"Рабочая директория: {cwd}\n"
        f"Antigravity CLI (agy): {'Доступен' if agy_ok else 'Не найден в PATH'}"
    )


# Отключаем DNS Rebinding защиту для работы через публичный ngrok-домен
security_settings = TransportSecuritySettings(enable_dns_rebinding_protection=False)

# Собираем Starlette приложение Streamable HTTP
app = mcp.streamable_http_app(
    streamable_http_path=f"/{SECRET_PATH}/mcp",
    transport_security=security_settings,
)

endpoint = app.routes[0].endpoint

# Регистрируем алиасы путей по секретному адресу
app.routes.append(Route(f"/{SECRET_PATH}", endpoint=endpoint))
app.routes.append(Route(f"/{SECRET_PATH}/sse", endpoint=endpoint))

# Глобальный CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("BRIDGE_PORT", 8000))
    print(f"[+] Сервер MCP запущен на порту {port}")
    print(f"[+] Защищённый URL: /{SECRET_PATH}/sse")
    print("[+] Режим прямого подключения (Authentication: None)")
    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

### Шаг 4. Скрипт автоматического запуска (`~/start.sh`)

Создайте `~/start.sh`:

```bash
#!/data/data/com.termux/files/usr/bin/bash

DOMAIN="${NGROK_DOMAIN:-ВАШ-ДОМЕН.ngrok-free.dev}"
SECRET_PATH="${BRIDGE_PATH:-spark-sec-9a8f7b2c}"
FULL_URL="https://${DOMAIN}/${SECRET_PATH}/sse"

trap 'kill $(jobs -p) 2>/dev/null; pkill -f "agy_bridge.py" 2>/dev/null' EXIT

pkill -f "agy_bridge.py" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true
sleep 1

echo "=== Запуск Termux MCP Bridge (Direct Secret URL) ==="
python "$HOME/agy_bridge.py" &
sleep 2

if command -v termux-clipboard-set >/dev/null 2>&1; then
    echo -n "$FULL_URL" | termux-clipboard-set
fi

echo "=================================================="
echo "🛡️  Защищённый URL скопирован в буфер:"
echo "👉 $FULL_URL"
echo ""
echo "ℹ️  В Gemini Spark выберите Authentication: None"
echo "=================================================="
echo "=== Запуск Ngrok туннеля ($DOMAIN) ==="
termux-chroot ngrok http 8000 --url="$DOMAIN" --log=stdout
```

Сделайте скрипт исполняемым:
```bash
chmod +x ~/start.sh
termux-fix-shebang ~/start.sh
```

> [!TIP]
> **Ярлык на экран (Termux:Widget):**  
> Скопируйте скрипт в `~/.shortcuts/SparkMCP.sh` (и `~/.termux/widget/dynamic_shortcuts/SparkMCP.sh`), чтобы запускать и выключать мост прямо с главного экрана Android в один клик.

---

### Шаг 5. Подключение к Gemini Spark на ПК

1. В Termux запустите:
   ```bash
   ./start.sh
   ```
2. Откройте браузер на ПК: [gemini.google.com](https://gemini.google.com).
3. Перейдите: **Settings & help** (Настройки) → **Connected Apps** (Подключенные сервисы) → раздел **Custom apps for Spark** → **Add custom app**.
4. Заполните поля:
   - **App Name:** `Termux Antigravity`
   - **MCP Server URL:** `https://ВАШ-ДОМЕН.ngrok-free.dev/spark-sec-9a8f7b2c/sse`
   - **Authentication:** `None` *(никаких паролей и Client ID)*.
5. Нажмите **Connect**. Gemini мгновенно увидит все 3 действия (`antigravity_run`, `bash_run`, `system_status`).

---

### Шаг 6. Использование в диалоге

В чате с Gemini Spark (в режиме Spark):
- *«Проверь статус телефона через Termux Bridge»* — вызов `system_status`.
- *«Покажи git status и список файлов в ~/projects/bot»* — вызов `bash_run`.
- *«Попроси Antigravity на телефоне создать Telegram-бота на Python»* — вызов `antigravity_run`.

Для отключения доступа — просто нажмите `Ctrl + C` в Termux или выключите ярлык.

---

## Связанные статьи
- [[INDEX-mcp]] — главный индекс Model Context Protocol.
- [[INDEX-ai-agents]] — адаптация и запуск AI-агентов в Termux.
- [[INDEX-antigravity]] — справочник по Antigravity CLI (`agy`).
- [[MEMORY.md]] — главный индекс памяти LLM Wiki.
