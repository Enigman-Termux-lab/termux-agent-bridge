#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# SparkMCP — Запуск и управление MCP-мостом для Gemini Spark в Termux
# Режим: Direct Secret URL + Streamable HTTP (Authentication: None)
# ==============================================================================
set -u

export PATH="$HOME/.local/bin:$HOME/bin:${PREFIX:-/data/data/com.termux/files/usr}/bin:${PATH:-}"

DOMAIN="${NGROK_DOMAIN:-your-subdomain.ngrok-free.dev}"
SECRET_PATH="${BRIDGE_PATH:-spark-secret-token-placeholder}"
FULL_URL="https://${DOMAIN}/${SECRET_PATH}/sse"

notify() {
    if command -v termux-toast >/dev/null 2>&1; then
        termux-toast "$1" >/dev/null 2>&1 || true
    fi
}

copy_url() {
    if command -v termux-clipboard-set >/dev/null 2>&1; then
        echo -n "$FULL_URL" | termux-clipboard-set >/dev/null 2>&1 || true
    fi
}

stop_bridge() {
    echo "Остановка процессов Spark MCP..."
    pkill -f "agy_bridge.py" 2>/dev/null || true
    pkill -f "ngrok" 2>/dev/null || true
    notify "🔴 Spark MCP остановлен"
    echo "Spark MCP полностью выключен."
}

# Проверяем, запущен ли уже мост
is_running=0
if pgrep -f "agy_bridge.py" >/dev/null 2>&1 || pgrep -f "ngrok" >/dev/null 2>&1; then
    is_running=1
fi

if [ "$is_running" -eq 1 ]; then
    echo "=================================================="
    echo "⚠️  Spark MCP уже запущен!"
    echo "=================================================="
    echo "1) Остановить мост (Stop)"
    echo "2) Перезапустить (Restart)"
    echo "3) Скопировать URL в буфер и выйти"
    echo ""
    read -r -t 8 -p "Выберите действие [1/2/3] (по умолч. 1): " choice || choice="1"
    echo ""

    case "$choice" in
        2)
            echo "Перезапуск..."
            stop_bridge
            sleep 1
            ;;
        3)
            copy_url
            notify "URL скопирован в буфер"
            echo "URL скопирован: $FULL_URL"
            exit 0
            ;;
        *)
            stop_bridge
            exit 0
            ;;
    esac
fi

# Очистка перед стартом
pkill -f "agy_bridge.py" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true
sleep 1

# Автоматическая остановка при закрытии сессии / Ctrl+C
trap 'stop_bridge' EXIT

clear 2>/dev/null || true
echo "=================================================="
echo "⚡ Aperture Science: Gemini Spark MCP Bridge ⚡"
echo "=================================================="
echo "Запуск сервера Python (Streamable HTTP)..."
python "$HOME/agy_bridge.py" &
sleep 2

copy_url
notify "🟢 Spark MCP запущен! URL в буфере"

echo "🟢 Статус: АКТИВЕН"
echo "🔗 URL:    $FULL_URL"
echo "📋 (Адрес скопирован в системный буфер обмена)"
echo "ℹ️  В Gemini Spark выберите Authentication: None"
echo "=================================================="
echo "Для остановки моста нажмите Ctrl + C"
echo "=================================================="
echo ""

# Запуск туннеля через chroot (решение DNS в Android)
exec termux-chroot ngrok http 8000 --url="$DOMAIN" --log=stdout
