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
SECRET_PATH = os.environ.get("BRIDGE_PATH", "spark-secret-token-placeholder")

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

# Регистрируем алиасы для защищённого пути
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
