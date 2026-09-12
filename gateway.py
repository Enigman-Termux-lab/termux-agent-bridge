"""
Termux Agent Gateway — Универсальный MCP-шлюз для Android/Termux
Совместим с OpenAI Codex, Claude Code, Google Antigravity, Gemini Spark, Cursor, Windsurf.
Поддерживает 4 профиля безопасности: MONITOR, WORKSPACE, INTERACTIVE, GODMODE.
Транспорт: Streamable HTTP (POST/GET) + SSE.
"""

import argparse
import asyncio
import json
import os
import platform
import re
import secrets
import select
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any
import uuid

# Обеспечиваем UTF-8 вывод на любой платформе (Windows cp1251, Linux, Termux)
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

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

# =============================================================================
# 🛡️ МОДУЛЬ БЕЗОПАСНОСТИ: ВАЛИДАЦИЯ И PUSH-ПОДТВЕРЖДЕНИЕ В ANDROID
# =============================================================================

# Паттерны потенциально опасных системных команд
DANGEROUS_PATTERNS = [
    # Удаление, перемещение и перезапись файлов/дисков
    (r"\b(rm|rmdir|srm|trash|shred|truncate|mv|unlink)\b", "Удаление или перемещение файлов/каталогов"),
    (r"\b(dd|mkfs[a-z0-9.]*|mke2fs|make_ext4fs|fdisk|sfdisk|parted)\b", "Низкоуровневая работа с дисками/разделами"),
    
    # Управление пакетами (изменение окружения Termux)
    (r"\b(pkg|apt|apt-get|dpkg|pacman)\b", "Установка/удаление системных пакетов"),
    
    # Повышение привилегий и выход из песочницы
    (r"\b(sudo|su|tsu|chroot|termux-chroot)\b", "Повышение привилегий или chroot"),
    
    # Остановка процессов, перезагрузка устройства
    (r"\b(kill|pkill|killall|reboot|shutdown|poweroff|init)\b", "Завершение процессов или перезагрузка"),
    
    # Модификация прав доступа
    (r"\b(chmod|chown|chgrp)\b", "Изменение прав доступа к файлам"),
    
    # Скачивание внешнего кода / сокеты
    (r"\b(curl|wget|fetch|nc|netcat|socat)\b", "Сетевая загрузка или сокет"),
    
    # Перенаправление вывода в системные каталоги, dotfiles или $PREFIX
    (r"(?:>|>>|&>)\s*(/|~/\.|\$HOME/\.|\$PREFIX/|\$PREFIX\b|~/\.termux|~/\.bash)", "Перенаправление вывода в системные пути или dotfiles"),
    
    # Запись в системные файлы через tee
    (r"\btee\b\s+(?:-[a-zA-Z]+\s+)*(?:/|~/\.|\$HOME/\.|\$PREFIX/|\$PREFIX\b|~/\.termux|~/\.bash)", "Запись в системные пути через tee"),
    
    # Конвейеры с передачей в shell (curl ... | bash)
    (r"\|\s*(sh|bash|zsh|dash)\b", "Выполнение скачанного скрипта через конвейер"),
    
    # Вложенный eval / exec
    (r"\b(eval|exec)\b", "Динамическое исполнение кода (eval/exec)"),
    
    # Доступ к секретам и ключам SSH
    (r"(\.ssh|id_rsa|id_ed25519|\.termux_agent_gateway\.env)", "Доступ к приватным ключам или конфигурации шлюза"),
    
    # Опасные операции git
    (r"\bgit\s+(push\s+.*--force|reset\s+--hard)\b", "Опасная операция Git (force push / reset hard)"),

    # Приватные или платные API Android через Termux:API
    (
        r"\b(termux-sms-send|termux-telephony-call|termux-camera-photo|termux-microphone-record|"
        r"termux-location|termux-contact-list|termux-call-log|termux-sms-list|termux-sensor)\b",
        "Доступ к приватным данным или звонкам/SMS Android (Termux:API)",
    ),

    # Fork bomb и опасные циклы
    (r":\(\)\s*\{", "Fork bomb сигнатура"),
]


class CommandValidator:
    """Валидатор команд на наличие опасных паттернов и деструктивных операций."""

    PATTERNS = DANGEROUS_PATTERNS

    @classmethod
    def is_dangerous(cls, command: str) -> tuple[bool, str]:
        """
        Проверяет команду на наличие опасных паттернов.
        Возвращает (True, причина) если команда опасна, иначе (False, "").
        """
        cmd_clean = command.strip()
        if not cmd_clean:
            return False, ""

        for pattern, reason in cls.PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return True, reason

        return False, ""


def is_dangerous_command(command: str) -> tuple[bool, str]:
    """Проверяет команду на наличие опасных паттернов."""
    return CommandValidator.is_dangerous(command)


def get_approvals_dir(custom_dir: str | None = None) -> str:
    """Возвращает путь к каталогу маркеров подтверждения."""
    if custom_dir:
        path = custom_dir
    elif "TERMUX_GATEWAY_APPROVALS_DIR" in os.environ:
        path = os.environ["TERMUX_GATEWAY_APPROVALS_DIR"]
    else:
        path = os.path.join(tempfile.gettempdir(), "termux_gateway_approvals")
    path = os.path.realpath(os.path.abspath(os.path.expandvars(os.path.expanduser(path))))
    os.makedirs(path, exist_ok=True)
    return path


def send_android_notification(
    request_id: str,
    command: str,
    reason: str,
    approve_path: str,
    deny_path: str,
) -> bool:
    """
    Отправляет уведомление в Android через termux-notification с кнопками подтверждения.
    """
    if not shutil.which("termux-notification"):
        return False

    short_cmd = (command[:55] + "...") if len(command) > 55 else command
    content = f"Команда: {short_cmd}\nПричина: {reason}"

    notification_id = f"gateway_{request_id}"
    cmd = [
        "termux-notification",
        "--id", notification_id,
        "--title", "⚠️ Termux Gateway: Запрос подтверждения",
        "--content", content,
        "--priority", "high",
        "--vibrate", "200,100,200",
        "--button1", "Разрешить",
        "--button1-action", f"touch {shlex.quote(approve_path)}",
        "--button2", "Заблокировать",
        "--button2-action", f"touch {shlex.quote(deny_path)}",
        "--on-delete-action", f"touch {shlex.quote(deny_path)}",
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        # Вибрация для привлечения внимания пользователя
        if shutil.which("termux-vibrate"):
            try:
                subprocess.run(["termux-vibrate", "-d", "250"], capture_output=True, timeout=2)
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"[!] Ошибка отправки termux-notification: {e}", file=sys.stderr)
        return False


def remove_android_notification(request_id: str) -> None:
    """Удаляет уведомление после завершения ожидания."""
    if shutil.which("termux-notification-remove"):
        try:
            notification_id = f"gateway_{request_id}"
            subprocess.run(["termux-notification-remove", "--id", notification_id], capture_output=True, timeout=3)
        except Exception:
            pass


def prompt_terminal(command: str, reason: str, timeout: int) -> bool:
    """Интерактивный запрос подтверждения в терминале, если запущен в TTY."""
    print("\n[⚠️ AI GATEWAY ЗАПРОС ПОДТВЕРЖДЕНИЯ]")
    print(f"Команда: {command}")
    print(f"Причина: {reason}")
    print(f"Разрешить выполнение? [y/N] (таймаут {timeout}с): ", end="", flush=True)

    if sys.platform != "win32":
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            reply = sys.stdin.readline().strip().lower()
            return reply in ("y", "yes", "д", "да")
        else:
            print("\n[Таймаут ожидания в терминале]")
            return False
    else:
        # Для Windows терминала простой fallback
        try:
            reply = input().strip().lower()
            return reply in ("y", "yes", "д", "да")
        except Exception:
            return False


class NotificationApprovalDaemon:
    """
    Демон интерактивного подтверждения выполнения опасных команд
    через push-уведомления Android (Termux:API) или TTY терминал.
    """

    @staticmethod
    def send_notification(
        request_id: str,
        command: str,
        reason: str,
        approve_path: str,
        deny_path: str,
    ) -> bool:
        return send_android_notification(request_id, command, reason, approve_path, deny_path)

    @staticmethod
    def remove_notification(request_id: str) -> None:
        remove_android_notification(request_id)

    @classmethod
    def request_approval(
        cls,
        command: str,
        reason: str = "",
        timeout: int = 45,
        approvals_dir: str | None = None,
    ) -> tuple[bool, str]:
        """
        Запрашивает подтверждение выполнения опасной команды у пользователя.
        
        1. Создает маркеры в каталоге approvals.
        2. Отправляет push-уведомление в Android (termux-notification) с кнопками «Разрешить» и «Заблокировать».
        3. Ожидает клика по кнопке до timeout секунд.
        4. При отсутствии termux-notification пытается спросить в интерактивном TTY.
        5. Если подтверждено -> (True, "Подтверждено пользователем").
           Если отклонено или таймаут -> (False, "Причина").
        """
        if os.environ.get("GATEWAY_AUTO_APPROVE") in ("1", "true", "True"):
            return True, "Автоматически подтверждено (GATEWAY_AUTO_APPROVE активен)"

        request_id = uuid.uuid4().hex[:8]
        work_dir = get_approvals_dir(custom_dir=approvals_dir)
        approve_path = os.path.join(work_dir, f"approve_{request_id}")
        deny_path = os.path.join(work_dir, f"deny_{request_id}")

        def cleanup():
            for p in (approve_path, deny_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            remove_android_notification(request_id)

        # Отправляем уведомление
        has_notification = send_android_notification(
            request_id=request_id,
            command=command,
            reason=reason,
            approve_path=approve_path,
            deny_path=deny_path,
        )

        if not has_notification:
            # Если termux-notification недоступен, проверяем интерактивный терминал
            if sys.stdin.isatty():
                approved = prompt_terminal(command, reason, timeout)
                cleanup()
                if approved:
                    return True, "Подтверждено пользователем в терминале"
                return False, "Отклонено пользователем в терминале"
            else:
                cleanup()
                return False, "Интерактивное подтверждение невозможно: termux-notification не найден и stdin не является TTY"

        # Цикл ожидания клика пользователя по кнопке в уведомлении
        start_time = time.time()
        try:
            while time.time() - start_time < timeout:
                if os.path.exists(approve_path):
                    cleanup()
                    return True, "Подтверждено пользователем через уведомление Android"

                if os.path.exists(deny_path):
                    cleanup()
                    return False, "Отклонено пользователем через уведомление Android"

                time.sleep(0.5)

            cleanup()
            return False, f"Превышен таймаут подтверждения ({timeout} сек)"
        except Exception as e:
            cleanup()
            return False, f"Ошибка в цикле ожидания подтверждения: {e}"


def request_approval(
    command: str,
    reason: str = "",
    timeout: int = 45,
    approvals_dir: str | None = None,
) -> tuple[bool, str]:
    """Функциональный алиас для NotificationApprovalDaemon.request_approval."""
    return NotificationApprovalDaemon.request_approval(command, reason, timeout, approvals_dir)

# Версия шлюза
GATEWAY_VERSION = "2.0.0"

# Поддерживаемые режимы безопасности
VALID_MODES = ("monitor", "workspace", "interactive", "godmode")


def load_env_file(filepath: str) -> None:
    """Загружает переменные из .env файла в os.environ, если они еще не заданы."""
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                else:
                    val = val.split("#", 1)[0].strip()
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"[!] Предупреждение: не удалось прочитать {filepath}: {e}", file=sys.stderr)


def load_config() -> dict[str, Any]:
    """Загружает настройки из окружения и конфигурационных файлов."""
    # 1. Загрузка из домашней директории Termux/Linux
    home_env = os.path.expanduser("~/.termux_agent_gateway.env")
    load_env_file(home_env)

    # 2. Загрузка из локального .env (при наличии)
    local_env = os.path.abspath(".env")
    load_env_file(local_env)

    mode = os.environ.get("GATEWAY_MODE", "interactive").lower().strip()
    if mode not in VALID_MODES:
        print(f"[!] Неизвестный режим '{mode}', применен 'interactive'", file=sys.stderr)
        mode = "interactive"

    port = int(os.environ.get("BRIDGE_PORT", "8000"))

    # Секретный путь URL
    secret_path = os.environ.get("SECRET_PATH", "").strip()
    if not secret_path:
        secret_path = f"gateway-{secrets.token_hex(12)}"

    old_secret_path = os.environ.get("OLD_SECRET_PATH", "").strip()

    # Рабочая директория для режима WORKSPACE
    raw_ws = os.environ.get("WORKSPACE_DIR", "").strip()
    if not raw_ws:
        raw_ws = "~/workspace"
    raw_ws = os.path.expandvars(os.path.expanduser(raw_ws))
    workspace_dir = os.path.realpath(os.path.abspath(raw_ws))
    os.makedirs(workspace_dir, exist_ok=True)

    approval_timeout = int(os.environ.get("APPROVAL_TIMEOUT", "45"))
    ngrok_domain = os.environ.get("NGROK_DOMAIN", "").strip()
    if not ngrok_domain:
        ngrok_domain = "your-domain.ngrok-free.dev"

    return {
        "mode": mode,
        "port": port,
        "secret_path": secret_path,
        "old_secret_path": old_secret_path,
        "workspace_dir": workspace_dir,
        "approval_timeout": approval_timeout,
        "ngrok_domain": ngrok_domain,
    }


def is_safe_workspace_path(target_path: str, workspace_dir: str) -> tuple[bool, str]:
    """
    Проверяет, что путь находится строго внутри разрешенного каталога workspace_dir.
    Предотвращает выход через '..' или симлинки.
    """
    abs_ws = os.path.realpath(os.path.abspath(os.path.expandvars(os.path.expanduser(workspace_dir))))
    expanded_target = os.path.expandvars(os.path.expanduser(target_path))
    if not os.path.isabs(expanded_target):
        resolved = os.path.realpath(os.path.abspath(os.path.join(abs_ws, expanded_target)))
    else:
        resolved = os.path.realpath(os.path.abspath(expanded_target))

    try:
        common = os.path.commonpath([resolved, abs_ws])
    except ValueError:
        return False, f"Путь '{target_path}' расположен на другом устройстве/диске"

    if common != abs_ws:
        return False, f"Доступ запрещен: путь '{target_path}' выходит за пределы workspace ({abs_ws})"

    return True, resolved


def is_safe_workspace_command(command: str) -> tuple[bool, str]:
    """
    Проверяет bash-команду на безопасность для режима WORKSPACE.
    Запрещает выход за пределы песочницы и изменение системных пакетов.
    """
    cmd = command.strip()
    # Запрещенные системные утилиты
    forbidden_tokens = [
        (r"\b(pkg|apt|apt-get|dpkg|pacman)\b", "Запрещено управление пакетами в режиме workspace"),
        (r"\b(sudo|su|tsu|chroot|termux-chroot)\b", "Запрещено повышение привилегий"),
        (r"\b(reboot|shutdown|poweroff|init)\b", "Запрещено управление питанием"),
        (r"\b(kill|pkill|killall)\b", "Запрещено завершение системных процессов"),
        (r"\b(mkfs|fdisk|parted|dd)\b", "Запрещена низкоуровневая запись на диск"),
    ]
    for pattern, reason in forbidden_tokens:
        if re.search(pattern, cmd, re.IGNORECASE):
            return False, reason

    # Запрет выхода за пределы workspace через пути в аргументах
    forbidden_paths = [
        (r"(\.\./|\.\.$|\.\.\s|\.\.[;|&])", "Запрещен относительный переход вверх ('..')"),
        (r"(/(data|sdcard|storage|etc|system|proc|sys)|\$PREFIX)\b", "Запрещен доступ к системным каталогам Android/Termux"),
        (r"~/\.", "Запрещен доступ к dotfiles в домашней директории"),
        (r"\bcd\s+(/|~|\$HOME)", "Запрещен переход за пределы каталога workspace"),
    ]
    for pattern, reason in forbidden_paths:
        if re.search(pattern, cmd):
            return False, reason

    return True, ""


def resolve_cwd(cwd: str | None) -> str | None:
    """Безопасно преобразует и проверяет рабочий каталог команды."""
    if not cwd:
        return None
    expanded = os.path.realpath(os.path.abspath(os.path.expandvars(os.path.expanduser(cwd.strip()))))
    return expanded if os.path.isdir(expanded) else None


def get_system_status_text(mode: str, workspace_dir: str) -> str:
    """Генерирует сводку о текущем состоянии системы."""
    cwd = os.getcwd()
    agy_available = shutil.which("agy") is not None
    termux_api_available = shutil.which("termux-notification") is not None
    is_termux = "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux")
    uname_str = platform.platform()

    return (
        f"=== Termux Agent Gateway v{GATEWAY_VERSION} ===\n"
        f"Режим безопасности: {mode.upper()}\n"
        f"Окружение: {'Android Termux' if is_termux else 'Linux/Host'}\n"
        f"Платформа: {uname_str}\n"
        f"Текущая директория: {cwd}\n"
        f"Рабочая директория (workspace): {workspace_dir}\n"
        f"Antigravity CLI (agy): {'Доступен' if agy_available else 'Не найден в PATH'}\n"
        f"Termux:API (уведомления): {'Доступен' if termux_api_available else 'Не найден'}\n"
        f"Python: {sys.version.split()[0]}"
    )


def get_battery_info_text() -> str:
    """Возвращает информацию о заряде аккумулятора телефона."""
    if shutil.which("termux-battery-status"):
        try:
            res = subprocess.run(
                ["termux-battery-status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                pct = data.get("percentage", "?")
                status = data.get("status", "Unknown")
                plugged = data.get("plugged", "Unknown")
                temp = data.get("temperature", "?")
                health = data.get("health", "Unknown")
                return (
                    f"Заряд батареи: {pct}%\n"
                    f"Статус: {status} (Питание: {plugged})\n"
                    f"Температура: {temp}°C\n"
                    f"Состояние: {health}"
                )
        except Exception as e:
            return f"Ошибка получения статуса батареи через Termux:API: {e}"

    # Fallback для стандартного Linux / Android sysfs
    sysfs_cap = "/sys/class/power_supply/battery/capacity"
    if os.path.exists(sysfs_cap):
        try:
            with open(sysfs_cap, "r") as f:
                return f"Заряд батареи (sysfs): {f.read().strip()}%"
        except Exception:
            pass

    return "Информация о батарее недоступна (утилита termux-battery-status не найдена)."


def read_tail_log(filepath: str, lines: int = 50, max_bytes: int = 512000) -> str:
    """Безопасно читает последние N строк текстового файла."""
    clean_path = filepath.strip()
    norm_check = clean_path.replace("\\", "/")
    if re.search(r"(\.ssh(/|$)|id_rsa|id_ed25519|\.termux_agent_gateway\.env)", norm_check, re.IGNORECASE):
        return "Ошибка: доступ к конфиденциальным файлам и ключам через tail_log запрещен."

    expanded = os.path.realpath(os.path.abspath(os.path.expandvars(os.path.expanduser(clean_path))))
    norm_expanded = expanded.replace("\\", "/")
    if re.search(r"(\.ssh(/|$)|id_rsa|id_ed25519|\.termux_agent_gateway\.env)", norm_expanded, re.IGNORECASE):
        return "Ошибка: доступ к конфиденциальным файлам и ключам через tail_log запрещен."

    if not os.path.exists(expanded):
        return f"Ошибка: файл '{filepath}' не найден."
    if os.path.isdir(expanded):
        return f"Ошибка: путь '{filepath}' является каталогом."

    try:
        size = os.path.getsize(expanded)
        with open(expanded, "r", encoding="utf-8", errors="replace") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
                content = f.read()
                split_lines = content.splitlines()
                selected = split_lines[-lines:]
                return f"[Показаны последние {len(selected)} строк (файл усечен)]\n" + "\n".join(selected)
            else:
                split_lines = f.readlines()
                selected = split_lines[-lines:]
                return "".join(selected).strip()
    except Exception as e:
        return f"Ошибка чтения лога: {e}"


def create_gateway_server(config: dict[str, Any]) -> FastMCP:
    """
    Фабрика MCP-сервера: создает экземпляр FastMCP и регистрирует
    инструменты строго в соответствии с выбранным профилем безопасности.
    """
    mode = config["mode"]
    secret_path = config["secret_path"]
    workspace_dir = config["workspace_dir"]
    approval_timeout = config["approval_timeout"]

    server_name = f"Termux Agent Gateway [{mode.upper()}]"
    security_settings = TransportSecuritySettings(enable_dns_rebinding_protection=False)

    mcp = FastMCP(
        name=server_name,
        streamable_http_path=f"/{secret_path}/mcp",
        transport_security=security_settings,
    )

    # =========================================================================
    # ОБЩИЕ ИНСТРУМЕНТЫ МОНИТОРИНГА (доступны во всех режимах)
    # =========================================================================

    @mcp.tool()
    def system_status() -> str:
        """Получить статус устройства Termux: режим безопасности, память, окружение и доступные утилиты."""
        return get_system_status_text(mode, workspace_dir)

    @mcp.tool()
    def battery_info() -> str:
        """Получить состояние аккумулятора смартфона (уровень заряда %, температура, статус зарядки)."""
        return get_battery_info_text()

    @mcp.tool()
    def tail_log(path: str, lines: int = 50) -> str:
        """Прочитать последние N строк лог-файла.

        Параметры:
        - path: путь к файлу лога.
        - lines: количество строк с конца (по умолчанию 50).
        """
        if mode == "workspace":
            safe, res = is_safe_workspace_path(path, workspace_dir)
            if not safe:
                return res
            return read_tail_log(res, lines=lines)
        return read_tail_log(path, lines=lines)

    # =========================================================================
    # РЕЖИМ 2: WORKSPACE (изолированная песочница)
    # =========================================================================
    if mode == "workspace":

        @mcp.tool()
        def workspace_bash(command: str) -> str:
            """Выполнить bash-команду строго внутри изолированной рабочей директории (~/workspace).
            Запрещены системные команды (pkg, apt, reboot, chroot) и доступ к путям за пределами каталога.
            """
            safe, reason = is_safe_workspace_command(command)
            if not safe:
                return f"[ОТКЛОНЕНО ПОЛИТИКОЙ БЕЗОПАСНОСТИ WORKSPACE] {reason}"

            try:
                res = subprocess.run(
                    command,
                    shell=True,
                    cwd=workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                output = ""
                if res.stdout:
                    output += res.stdout
                if res.stderr:
                    output += ("\n[STDERR]\n" if output else "") + res.stderr
                return output.strip() if output else "[Команда успешно выполнена без вывода]"
            except subprocess.TimeoutExpired:
                return "Ошибка: превышен таймаут выполнения команды (60 сек)."
            except Exception as e:
                return f"Ошибка выполнения команды: {e}"

        @mcp.tool()
        def file_read(path: str, offset: int = 0, limit: int = 8000) -> str:
            """Прочитать содержимое файла внутри каталога workspace.

            Параметры:
            - path: относительный или абсолютный путь к файлу внутри workspace.
            - offset: смещение в символах.
            - limit: максимальное количество символов для чтения.
            """
            safe, full_path = is_safe_workspace_path(path, workspace_dir)
            if not safe:
                return full_path

            if not os.path.exists(full_path):
                return f"Ошибка: файл '{path}' не существует."
            if os.path.isdir(full_path):
                return f"Ошибка: путь '{path}' является директорией."

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(offset)
                    data = f.read(limit)
                return data
            except Exception as e:
                return f"Ошибка чтения файла: {e}"

        @mcp.tool()
        def file_write(path: str, content: str, append: bool = False) -> str:
            """Записать или дополнить файл внутри каталога workspace.

            Параметры:
            - path: относительный или абсолютный путь к файлу внутри workspace.
            - content: текст для записи.
            - append: True для добавления в конец файла, False для перезаписи.
            """
            safe, full_path = is_safe_workspace_path(path, workspace_dir)
            if not safe:
                return full_path

            try:
                parent_dir = os.path.dirname(full_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                write_mode = "a" if append else "w"
                with open(full_path, write_mode, encoding="utf-8") as f:
                    f.write(content)
                size = os.path.getsize(full_path)
                action_str = "дополнен" if append else "записан"
                return f"Файл '{path}' успешно {action_str} (размер: {size} байт)."
            except Exception as e:
                return f"Ошибка записи файла: {e}"

    # =========================================================================
    # РЕЖИМ 3: INTERACTIVE (интерактивное подтверждение опасных команд)
    # =========================================================================
    elif mode == "interactive":

        @mcp.tool()
        def bash_run(command: str, cwd: str | None = None) -> str:
            """Выполнить bash-команду в Termux.
            Безопасные команды (ls, pwd, git, cat, ps) исполняются мгновенно.
            Опасные команды (rm, pkg, curl|sh, kill, chmod) запрашивают подтверждение кнопкой в push-уведомлении Android.
            """
            target_cwd = resolve_cwd(cwd)
            is_dang, reason = CommandValidator.is_dangerous(command)

            prefix_msg = ""
            if is_dang:
                print(f"[*] Запрос подтверждения опасной команды: {command} (Причина: {reason})")
                approved, verdict = NotificationApprovalDaemon.request_approval(
                    command=command,
                    reason=reason,
                    timeout=approval_timeout,
                )
                if not approved:
                    return f"[ОТКЛОНЕНО ПОЛЬЗОВАТЕЛЕМ НА ТЕЛЕФОНЕ]\nКоманда: {command}\nПричина: {verdict}"
                prefix_msg = f"[ПОДТВЕРЖДЕНО ПОЛЬЗОВАТЕЛЕМ НА ТЕЛЕФОНЕ: {verdict}]\n"

            try:
                res = subprocess.run(
                    command,
                    shell=True,
                    cwd=target_cwd,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                output = ""
                if res.stdout:
                    output += res.stdout
                if res.stderr:
                    output += ("\n[STDERR]\n" if output else "") + res.stderr
                body = output.strip() if output else "[Команда успешно выполнена без вывода]"
                return prefix_msg + body
            except subprocess.TimeoutExpired:
                return prefix_msg + "Ошибка: превышен таймаут выполнения команды (90 сек)."
            except Exception as e:
                return prefix_msg + f"Ошибка выполнения команды: {e}"

    # =========================================================================
    # РЕЖИМ 4: GODMODE (полный неограниченный доступ)
    # =========================================================================
    elif mode == "godmode":

        @mcp.tool()
        def bash_run(command: str, cwd: str | None = None) -> str:
            """Выполнить любую bash-команду в Termux без ограничений (режим GODMODE)."""
            target_cwd = resolve_cwd(cwd)
            try:
                res = subprocess.run(
                    command,
                    shell=True,
                    cwd=target_cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                output = ""
                if res.stdout:
                    output += res.stdout
                if res.stderr:
                    output += ("\n[STDERR]\n" if output else "") + res.stderr
                return output.strip() if output else "[Команда успешно выполнена без вывода]"
            except subprocess.TimeoutExpired:
                return "Ошибка: превышен таймаут выполнения команды (300 сек)."
            except Exception as e:
                return f"Ошибка выполнения команды: {e}"

        @mcp.tool()
        def antigravity_run(prompt: str, continue_session: bool = True) -> str:
            """Запустить кодинг-агента Antigravity CLI (agy) с заданной задачей.

            Параметры:
            - prompt: инструкция для агента Antigravity.
            - continue_session: True для сохранения контекста предыдущей сессии (-c).
            """
            cmd = ["agy", "--dangerously-skip-permissions"]
            if continue_session:
                cmd.append("-c")
            cmd.extend(["-p", prompt])

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                out = res.stdout if res.stdout else res.stderr
                return out.strip() if out else "[Antigravity выполнил задачу без вывода]"
            except subprocess.TimeoutExpired:
                return "Ошибка: превышен таймаут Antigravity CLI (300 сек)."
            except Exception as e:
                return f"Ошибка вызова Antigravity CLI: {e}"

        @mcp.tool()
        def termux_api(api_command: str, args: list[str] | None = None) -> str:
            """Прямой вызов утилит Termux:API (termux-toast, termux-vibrate, termux-clipboard-set, etc.).

            Параметры:
            - api_command: название утилиты (например, 'termux-toast', 'termux-vibrate').
            - args: список строковых аргументов.
            """
            full_cmd = [api_command]
            if args:
                full_cmd.extend(args)

            try:
                res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=15)
                out = res.stdout.strip()
                err = res.stderr.strip()
                if out and err:
                    return f"{out}\n[STDERR]: {err}"
                return out if out else (err if err else "[Termux:API команда выполнена успешно]")
            except Exception as e:
                return f"Ошибка вызова Termux:API: {e}"

    return mcp


def build_app(config: dict[str, Any]):
    """Создает и настраивает Starlette-приложение шлюза с маршрутами и CORS."""
    mcp_server = create_gateway_server(config)
    secret_path = config["secret_path"]
    old_secret_path = config.get("old_secret_path", "")
    mode = config["mode"]

    app = mcp_server.streamable_http_app()
    endpoint = app.routes[0].endpoint

    # Регистрируем алиасы для секретного пути
    app.routes.append(Route(f"/{secret_path}", endpoint=endpoint))
    app.routes.append(Route(f"/{secret_path}/sse", endpoint=endpoint))

    # Healthcheck endpoints
    async def health_check_endpoint(request):
        tools = await mcp_server.list_tools()
        return JSONResponse({
            "status": "ok",
            "gateway": "Termux Agent Gateway",
            "version": GATEWAY_VERSION,
            "mode": mode,
            "tools": [t.name for t in tools],
        })

    app.routes.append(Route(f"/{secret_path}/health", endpoint=health_check_endpoint))
    app.routes.append(Route("/health", endpoint=health_check_endpoint))

    # Алиасы для старого секретного пути (обратная совместимость)
    if old_secret_path:
        app.routes.append(Route(f"/{old_secret_path}", endpoint=endpoint))
        app.routes.append(Route(f"/{old_secret_path}/sse", endpoint=endpoint))
        app.routes.append(Route(f"/{old_secret_path}/mcp", endpoint=endpoint))

    # CORS Middleware для кросс-доменных запросов браузерных агентов (Spark, Web Codex)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    return app, mcp_server


def print_banner(config: dict[str, Any]) -> None:
    """Отображает цветной информационный баннер при старте шлюза."""
    mode = config["mode"]
    port = config["port"]
    secret_path = config["secret_path"]
    domain = config["ngrok_domain"]
    full_url = f"https://{domain}/{secret_path}/sse" if domain else f"http://127.0.0.1:{port}/{secret_path}/sse"

    colors = {
        "monitor": "\033[92m",      # Зеленый
        "workspace": "\033[93m",    # Желтый
        "interactive": "\033[94m",  # Синий/Бирюзовый
        "godmode": "\033[91m",      # Красный
        "reset": "\033[0m",
        "bold": "\033[1m",
    }
    c = colors.get(mode, "")
    reset = colors["reset"]
    bold = colors["bold"]

    print("=" * 64)
    print(f"{bold}🚀 Termux Agent Gateway v{GATEWAY_VERSION}{reset}")
    print("=" * 64)
    print(f"Режим безопасности: {c}{bold}{mode.upper()}{reset}")
    if mode == "monitor":
        print("ℹ️  Только чтение. Bash и модификация файлов отключены.")
    elif mode == "workspace":
        print(f"ℹ️  Изоляция в песочнице: {config['workspace_dir']}")
    elif mode == "interactive":
        print("ℹ️  Интерактивный режим: опасные команды требуют клика в уведомлении Android.")
    elif mode == "godmode":
        print(f"{colors['godmode']}{bold}⚠️  ВНИМАНИЕ: GODMODE активен! Полный неограниченный доступ к Termux!{reset}")

    print(f"Порт:               {port}")
    print(f"Секретный путь:     /{secret_path}")
    print(f"URL для подключения: {bold}{full_url}{reset}")
    print("Транспорт:          Streamable HTTP (POST / GET) & SSE")
    print("Аутентификация:     None (защищено секретным capability URL)")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(description="Termux Agent Gateway Server")
    parser.add_argument("--mode", choices=VALID_MODES, help="Режим безопасности (monitor, workspace, interactive, godmode)")
    parser.add_argument("--port", type=int, help="Порт сервера (по умолчанию 8000)")
    parser.add_argument("--secret", help="Секретный префикс пути URL")
    args = parser.parse_args()

    config = load_config()
    if args.mode:
        config["mode"] = args.mode
    if args.port:
        config["port"] = args.port
    if args.secret:
        config["secret_path"] = args.secret

    print_banner(config)
    app, _ = build_app(config)

    uvicorn.run(app, host="0.0.0.0", port=config["port"], log_level="info")


if __name__ == "__main__":
    main()
