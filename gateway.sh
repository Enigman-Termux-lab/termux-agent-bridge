#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# 🚀 Termux Agent Gateway — Launcher & Setup Wizard for Android / Termux
# Совместим с: OpenAI Codex, Claude Code, Google Antigravity, Gemini Spark
# ==============================================================================
set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/bin:${PREFIX:-/data/data/com.termux/files/usr}/bin:${PATH:-}"

CONFIG_FILE="$HOME/.termux_agent_gateway.env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ANSI Colors
CLR_RESET="\033[0m"
CLR_BOLD="\033[1m"
CLR_RED="\033[91m"
CLR_GREEN="\033[92m"
CLR_YELLOW="\033[93m"
CLR_BLUE="\033[94m"
CLR_CYAN="\033[96m"

# Utility: notifications
notify() {
    local msg="$1"
    if command -v termux-toast >/dev/null 2>&1; then
        termux-toast "$msg" >/dev/null 2>&1 || true
    fi
}

copy_to_clipboard() {
    local text="$1"
    if command -v termux-clipboard-set >/dev/null 2>&1; then
        printf "%s" "$text" | termux-clipboard-set >/dev/null 2>&1 || true
        return 0
    fi
    return 1
}

# ------------------------------------------------------------------------------
# 1. Wizard: проверка зависимостей и первичная настройка
# ------------------------------------------------------------------------------
check_dependencies() {
    echo -e "${CLR_CYAN}[*] Проверка системных компонентов...${CLR_RESET}"

    # Python
    if ! command -v python >/dev/null 2>&1; then
        echo -e "${CLR_YELLOW}[!] Python не обнаружен. Устанавливаем...${CLR_RESET}"
        pkg update -y && pkg install -y python
    fi

    # Termux:API
    if ! command -v termux-notification >/dev/null 2>&1; then
        echo -e "${CLR_YELLOW}[!] Пакет termux-api не обнаружен.${CLR_RESET}"
        echo -e "    Устанавливаем: pkg install -y termux-api"
        pkg install -y termux-api || echo -e "${CLR_RED}[!] Установите Termux:API из F-Droid!${CLR_RESET}"
    fi

    # Python packages
    if ! python -c "import mcp, starlette, uvicorn" >/dev/null 2>&1; then
        echo -e "${CLR_YELLOW}[!] Установка необходимых Python-пакетов (mcp, starlette, uvicorn)...${CLR_RESET}"
        pip install --upgrade pip || true
        pip install mcp starlette uvicorn || pip install --break-system-packages mcp starlette uvicorn
    fi

    # Ngrok
    if ! command -v ngrok >/dev/null 2>&1; then
        echo -e "${CLR_YELLOW}[!] Утилита ngrok не найдена.${CLR_RESET}"
        echo -e "    Попытка установки из репозитория TUR (Termux User Repository)..."
        if pkg install -y tur-repo 2>/dev/null && pkg install -y ngrok 2>/dev/null; then
            echo -e "${CLR_GREEN}[+] ngrok успешно установлен из TUR!${CLR_RESET}"
        else
            echo -e "${CLR_RED}[!] Не удалось автоматически установить ngrok.${CLR_RESET}"
            echo -e "    Скачайте Linux ARM64 binary с dashboard.ngrok.com и поместите в \$PREFIX/bin/ngrok"
        fi
    fi
}

run_onboarding_wizard() {
    clear 2>/dev/null || true
    echo -e "${CLR_CYAN}${CLR_BOLD}================================================================${CLR_RESET}"
    echo -e "${CLR_CYAN}${CLR_BOLD}🚀 Termux Agent Gateway — Мастер первоначальной настройки${CLR_RESET}"
    echo -e "${CLR_CYAN}${CLR_BOLD}================================================================${CLR_RESET}"
    echo -e "Добро пожаловать! Давайте настроим шлюз за 1 минуту.\n"

    check_dependencies

    echo ""
    echo -e "${CLR_BOLD}--- Шаг 1/3: Настройка Ngrok ---${CLR_RESET}"
    
    # Проверяем токен ngrok
    local current_token=""
    if [ -f "$HOME/.config/ngrok/ngrok.yml" ]; then
        current_token=$(grep -oE "authtoken:\s*.+" "$HOME/.config/ngrok/ngrok.yml" | awk '{print $2}' || true)
    fi

    if [ -z "$current_token" ]; then
        echo -e "Введите ваш Authtoken Ngrok (из личного кабинета dashboard.ngrok.com):"
        echo -e "${CLR_YELLOW}(Токен хранится ТОЛЬКО локально на телефоне и никуда не передается!)${CLR_RESET}"
        read -r -p "Ngrok Token (Enter для пропуска): " input_token
        if [ -n "$input_token" ]; then
            if command -v ngrok >/dev/null 2>&1; then
                ngrok config add-authtoken "$input_token"
                echo -e "${CLR_GREEN}[+] Токен ngrok успешно сохранен!${CLR_RESET}"
            fi
        fi
    else
        echo -e "${CLR_GREEN}[+] Ngrok authtoken уже настроен в системе.${CLR_RESET}"
    fi

    # Ngrok Domain
    local default_domain="unstaffed-clamshell-overplant.ngrok-free.dev"
    echo ""
    echo -e "Введите статический домен ngrok (Static Domain):"
    read -r -p "Домен [$default_domain]: " input_domain
    local domain="${input_domain:-$default_domain}"

    echo ""
    echo -e "${CLR_BOLD}--- Шаг 2/3: Профиль безопасности ---${CLR_RESET}"
    echo -e " 1) ${CLR_GREEN}MONITOR${CLR_RESET}     - Риск 0/5. Только чтение: статус, батарея, логи. Bash отключен."
    echo -e " 2) ${CLR_YELLOW}WORKSPACE${CLR_RESET}   - Риск 2/5. Песочница: команды и файлы строго в ~/workspace."
    echo -e " 3) ${CLR_BLUE}INTERACTIVE${CLR_RESET} - Риск 1.5/5. [РЕКОМЕНДУЕТСЯ] Опасные команды требуют push в Android."
    echo -e " 4) ${CLR_RED}GODMODE${CLR_RESET}     - Риск 5/5. Полный неограниченный доступ к Termux и agy CLI."
    read -r -p "Выберите профиль [1-4] (по умолчанию 3): " input_mode_idx
    local mode="interactive"
    case "$input_mode_idx" in
        1) mode="monitor" ;;
        2) mode="workspace" ;;
        3) mode="interactive" ;;
        4) mode="godmode" ;;
        *) mode="interactive" ;;
    esac

    echo ""
    echo -e "${CLR_BOLD}--- Шаг 3/3: Генерация Capability Secret ---${CLR_RESET}"
    local generated_secret
    generated_secret="gateway-$(python -c 'import secrets; print(secrets.token_hex(12))' 2>/dev/null || od -vN 12 -An -tx1 /dev/urandom | tr -d ' \n')"
    echo -e "[+] Сгенерирован уникальный секретный путь: ${CLR_BOLD}/$generated_secret${CLR_RESET}"

    # Создаем папку workspace
    mkdir -p "$HOME/workspace"

    # Записываем конфиг
    cat <<EOF > "$CONFIG_FILE"
# ==============================================================================
# 🚀 Termux Agent Gateway Configuration
# ==============================================================================
GATEWAY_MODE="$mode"
BRIDGE_PORT=8000
NGROK_DOMAIN="$domain"
SECRET_PATH="$generated_secret"
OLD_SECRET_PATH=""
WORKSPACE_DIR="\$HOME/workspace"
APPROVAL_TIMEOUT=45
EOF
    chmod 600 "$CONFIG_FILE"
    echo -e "${CLR_GREEN}${CLR_BOLD}[✓] Конфигурация сохранена в $CONFIG_FILE${CLR_RESET}\n"
    sleep 1
}

# ------------------------------------------------------------------------------
# 2. Управление процессами (Stop, Status)
# ------------------------------------------------------------------------------
stop_gateway() {
    echo -e "${CLR_YELLOW}[*] Остановка Termux Agent Gateway...${CLR_RESET}"
    pkill -f "gateway.py" 2>/dev/null || true
    pkill -f "agy_bridge.py" 2>/dev/null || true
    pkill -f "ngrok" 2>/dev/null || true
    notify "🔴 Termux Agent Gateway остановлен"
    echo -e "${CLR_GREEN}[✓] Шлюз успешно остановлен.${CLR_RESET}"
}

show_status() {
    local py_running=0
    local ngrok_running=0
    if pgrep -f "gateway.py" >/dev/null 2>&1 || pgrep -f "agy_bridge.py" >/dev/null 2>&1; then
        py_running=1
    fi
    if pgrep -f "ngrok" >/dev/null 2>&1; then
        ngrok_running=1
    fi

    echo -e "${CLR_CYAN}${CLR_BOLD}=== Termux Agent Gateway: Статус ===${CLR_RESET}"
    if [ "$py_running" -eq 1 ]; then
        echo -e "Сервер Python:    ${CLR_GREEN}АКТИВЕН (PID $(pgrep -f 'gateway.py\|agy_bridge.py' | tr '\n' ' '))${CLR_RESET}"
    else
        echo -e "Сервер Python:    ${CLR_RED}ВЫКЛЮЧЕН${CLR_RESET}"
    fi

    if [ "$ngrok_running" -eq 1 ]; then
        echo -e "Туннель Ngrok:    ${CLR_GREEN}АКТИВЕН (PID $(pgrep -f 'ngrok' | tr '\n' ' '))${CLR_RESET}"
    else
        echo -e "Туннель Ngrok:    ${CLR_RED}ВЫКЛЮЧЕН${CLR_RESET}"
    fi

    if [ -f "$CONFIG_FILE" ]; then
        # shellcheck disable=SC1090
        . "$CONFIG_FILE"
        echo -e "Режим:            ${CLR_BOLD}${GATEWAY_MODE:-interactive}${CLR_RESET}"
        echo -e "URL:              ${CLR_BOLD}https://${NGROK_DOMAIN:-localhost}/${SECRET_PATH:-gateway}/sse${CLR_RESET}"
    fi
    echo "======================================"
}

# ------------------------------------------------------------------------------
# 3. Главный запуск (Run Gateway)
# ------------------------------------------------------------------------------
start_gateway() {
    if [ ! -f "$CONFIG_FILE" ]; then
        run_onboarding_wizard
    fi

    # shellcheck disable=SC1090
    . "$CONFIG_FILE"

    local port="${BRIDGE_PORT:-8000}"
    local domain="${NGROK_DOMAIN:-unstaffed-clamshell-overplant.ngrok-free.dev}"
    local secret="${SECRET_PATH:-gateway-default}"
    local mode="${GATEWAY_MODE:-interactive}"
    local full_url="https://${domain}/${secret}/sse"

    # Проверка, запущен ли уже
    if pgrep -f "gateway.py" >/dev/null 2>&1 || pgrep -f "agy_bridge.py" >/dev/null 2>&1; then
        echo -e "${CLR_YELLOW}[!] Шлюз уже запущен!${CLR_RESET}"
        echo -e "1) Перезапустить (Restart)"
        echo -e "2) Остановить (Stop)"
        echo -e "3) Скопировать URL в буфер и выйти"
        read -r -t 8 -p "Выберите действие [1/2/3] (по умолчанию 3): " choice || choice="3"
        case "$choice" in
            1) stop_gateway; sleep 1 ;;
            2) stop_gateway; exit 0 ;;
            *)
                copy_to_clipboard "$full_url"
                notify "URL скопирован в буфер"
                echo -e "${CLR_GREEN}URL скопирован в буфер: ${full_url}${CLR_RESET}"
                exit 0
                ;;
        esac
    fi

    # Очистка старых зависших процессов
    pkill -f "gateway.py" 2>/dev/null || true
    pkill -f "agy_bridge.py" 2>/dev/null || true
    pkill -f "ngrok" 2>/dev/null || true
    sleep 1

    # Регистрация обработчика выхода
    trap 'stop_gateway' EXIT INT TERM

    clear 2>/dev/null || true
    echo -e "${CLR_CYAN}${CLR_BOLD}================================================================${CLR_RESET}"
    echo -e "${CLR_CYAN}${CLR_BOLD}🚀 Запуск Termux Agent Gateway v2.0.0${CLR_RESET}"
    echo -e "${CLR_CYAN}${CLR_BOLD}================================================================${CLR_RESET}"
    echo -e "Режим безопасности: ${CLR_BOLD}${mode^^}${CLR_RESET}"
    echo -e "Порт:               ${port}"
    echo -e "Путь:               /${secret}"
    echo -e "Ngrok Домен:        ${domain}"
    echo -e "Транспорт:          Streamable HTTP / SSE"
    echo -e "----------------------------------------------------------------"

    # Запуск сервера Python
    local server_script="$SCRIPT_DIR/gateway.py"
    if [ ! -f "$server_script" ]; then
        server_script="$SCRIPT_DIR/agy_bridge.py"
    fi

    echo -e "[*] Запуск Python MCP Server ($server_script)..."
    python "$server_script" &
    local py_pid=$!

    # Ждем старта uvicorn
    sleep 2

    # Копируем URL в буфер обмена Android
    if copy_to_clipboard "$full_url"; then
        echo -e "${CLR_GREEN}[✓] Секретный URL скопирован в системный буфер обмена!${CLR_RESET}"
    fi
    notify "🟢 Gateway запущен! [${mode^^}]"

    echo -e "\n${CLR_GREEN}${CLR_BOLD}════════════════════════════════════════════════════════════════${CLR_RESET}"
    echo -e "🔗 ${CLR_BOLD}URL ДЛЯ ПОДКЛЮЧЕНИЯ АГЕНТОВ:${CLR_RESET}"
    echo -e "   ${CLR_CYAN}${CLR_BOLD}${full_url}${CLR_RESET}"
    echo -e "${CLR_GREEN}${CLR_BOLD}════════════════════════════════════════════════════════════════${CLR_RESET}"
    echo -e "📌 ${CLR_BOLD}OpenAI Codex:${CLR_RESET}"
    echo -e "   Settings → MCP servers → Add server"
    echo -e "   • Name:           Termux MCP Bridge"
    echo -e "   • Type:           Streamable HTTP"
    echo -e "   • URL:            ${full_url}"
    echo -e "   • Authentication: None"
    echo -e "----------------------------------------------------------------"
    echo -e "📌 ${CLR_BOLD}Claude Code CLI:${CLR_RESET}"
    echo -e "   claude mcp add termux --transport http ${full_url}"
    echo -e "----------------------------------------------------------------"
    echo -e "📌 ${CLR_BOLD}Gemini Spark:${CLR_RESET}"
    echo -e "   Connected Apps → Custom apps for Spark → URL: ${full_url}"
    echo -e "${CLR_GREEN}${CLR_BOLD}════════════════════════════════════════════════════════════════${CLR_RESET}"
    echo -e "Для завершения работы шлюза нажмите ${CLR_BOLD}Ctrl + C${CLR_RESET}\n"

    # Запуск ngrok туннеля (с обходом DNS Android через termux-chroot при наличии)
    local ngrok_args=(http "$port" --log=stdout)
    if [ -n "$domain" ]; then
        ngrok_args+=(--url="$domain")
    fi

    if command -v termux-chroot >/dev/null 2>&1; then
        termux-chroot ngrok "${ngrok_args[@]}" || true
    else
        ngrok "${ngrok_args[@]}" || true
    fi
}

# ------------------------------------------------------------------------------
# 4. CLI Маршрутизация аргументов
# ------------------------------------------------------------------------------
ACTION="${1:-run}"

case "$ACTION" in
    run|"")
        start_gateway
        ;;
    start)
        start_gateway
        ;;
    stop)
        stop_gateway
        ;;
    restart)
        stop_gateway
        sleep 1
        start_gateway
        ;;
    status)
        show_status
        ;;
    config)
        run_onboarding_wizard
        ;;
    copy)
        if [ -f "$CONFIG_FILE" ]; then
            # shellcheck disable=SC1090
            . "$CONFIG_FILE"
            url="https://${NGROK_DOMAIN:-localhost}/${SECRET_PATH:-gateway}/sse"
            copy_to_clipboard "$url"
            echo -e "${CLR_GREEN}URL скопирован: $url${CLR_RESET}"
            notify "URL скопирован"
        else
            echo -e "${CLR_RED}[!] Конфигурация не найдена. Запустите: ./gateway.sh config${CLR_RESET}"
        fi
        ;;
    --help|-h)
        echo "Использование: ./gateway.sh [команда]"
        echo "Команды:"
        echo "  run (по умолч.) - Запустить шлюз и туннель ngrok"
        echo "  stop            - Остановить все процессы шлюза"
        echo "  restart         - Перезапустить шлюз"
        echo "  status          - Показать статус работы"
        echo "  config          - Повторно запустить мастер настройки"
        echo "  copy            - Скопировать URL в буфер обмена Android"
        ;;
    *)
        echo "Неизвестная команда '$ACTION'. Используйте: ./gateway.sh --help"
        exit 1
        ;;
esac
