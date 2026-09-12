"""
Termux Agent Gateway — Approval Daemon & Security Validator
Модуль валидации команд и интерактивного подтверждения через уведомления Android (termux-notification).
"""

import os
import re
import select
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

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


def is_dangerous_command(command: str) -> tuple[bool, str]:
    """
    Проверяет команду на наличие опасных паттернов.
    Возвращает (True, причина) если команда опасна, иначе (False, "").
    """
    cmd_clean = command.strip()
    if not cmd_clean:
        return False, ""

    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return True, reason

    return False, ""


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
    print(f"\n[⚠️ AI GATEWAY ЗАПРОС ПОДТВЕРЖДЕНИЯ]")
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


def request_approval(
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
