"""
Termux MCP Bridge для Gemini Spark, OpenAI Codex и универсальных AI-агентов.
Обратно совместимый адаптер к Termux Agent Gateway.
Прямое надёжное подключение без OAuth. Защищено секретным адресом.
Поддерживает современный Streamable HTTP транспорт (POST/GET) и SSE.
"""

import os
import sys
import uvicorn

# Обеспечиваем UTF-8 вывод на любой платформе
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import gateway

# Загружаем настройки из ~/.termux_agent_gateway.env или .env если есть
config = gateway.load_config()

# Замена опубликованного ранее в чате пути spark-693cff05cc2e0b79420ffe3d
# Новый защищенный секретный путь:
DEFAULT_NEW_SECRET = "spark-7e4a19b8c0d3e5f2a1b4c6d8"
# Старый опубликованный путь для плавной обратной совместимости:
DEFAULT_OLD_SECRET = "spark-693cff05cc2e0b79420ffe3d"

NEW_SECRET_PATH = os.environ.get("SECRET_PATH") or os.environ.get("BRIDGE_PATH") or config.get("secret_path") or DEFAULT_NEW_SECRET
OLD_SECRET_PATH = os.environ.get("OLD_SECRET_PATH") or config.get("old_secret_path") or DEFAULT_OLD_SECRET

# Обновляем конфигурацию шлюза
config["secret_path"] = NEW_SECRET_PATH
config["old_secret_path"] = OLD_SECRET_PATH

# Режим по умолчанию для agy_bridge: interactive (с подтверждением опасных команд)
if "GATEWAY_MODE" not in os.environ:
    config["mode"] = "interactive"

if not config.get("ngrok_domain"):
    config["ngrok_domain"] = "unstaffed-clamshell-overplant.ngrok-free.dev"

app, mcp = gateway.build_app(config)

if __name__ == "__main__":
    port = config["port"]
    domain = config["ngrok_domain"]
    url_base = f"https://{domain}" if domain else f"http://localhost:{port}"

    print("=" * 64)
    print("⚡ Termux MCP Bridge (Streamable HTTP / SSE) ⚡")
    print("=" * 64)
    print(f"[+] Сервер MCP запущен на порту:   {port}")
    print(f"[+] Режим безопасности:           {config['mode'].upper()}")
    print(f"[+] Новый защищённый URL (Codex): {url_base}/{NEW_SECRET_PATH}/sse")
    print(f"[+] Режим аутентификации:         Authentication: None")
    print(f"[+] Совместимый старый путь:      /{OLD_SECRET_PATH}/sse (активен)")
    print("=" * 64)
    print("ℹ️  В Codex: Settings → MCP servers → Add server:")
    print("    Name:           Termux MCP Bridge")
    print("    Type:           Streamable HTTP")
    print(f"    URL:            {url_base}/{NEW_SECRET_PATH}/sse")
    print("    Authentication: None")
    print("=" * 64)

    uvicorn.run(app, host="0.0.0.0", port=port)
