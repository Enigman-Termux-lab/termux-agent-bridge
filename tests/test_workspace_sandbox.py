"""
Тесты изоляции и песочницы для режима WORKSPACE.
"""

import os
import shutil
import tempfile
import unittest

import gateway


class TestWorkspaceSandbox(unittest.TestCase):
    def setUp(self):
        self.temp_ws = tempfile.mkdtemp(prefix="test_gateway_ws_")

    def tearDown(self):
        if os.path.exists(self.temp_ws):
            shutil.rmtree(self.temp_ws, ignore_errors=True)

    def test_safe_path_inside_workspace(self):
        # Файл внутри
        ok, res = gateway.is_safe_workspace_path("sub/test.txt", self.temp_ws)
        self.assertTrue(ok)
        self.assertTrue(res.startswith(os.path.realpath(self.temp_ws)))

        # Абсолютный путь внутри
        abs_in = os.path.join(self.temp_ws, "hello.py")
        ok, res = gateway.is_safe_workspace_path(abs_in, self.temp_ws)
        self.assertTrue(ok)

    def test_unsafe_path_traversal(self):
        # Попытка выхода через '..'
        ok, res = gateway.is_safe_workspace_path("../outside.txt", self.temp_ws)
        self.assertFalse(ok)
        self.assertIn("выходит за пределы", res)

        # Попытка многократного выхода
        ok, res = gateway.is_safe_workspace_path("sub/../../escape.txt", self.temp_ws)
        self.assertFalse(ok)

        # Доступ к корню
        ok, res = gateway.is_safe_workspace_path("/data/data/com.termux", self.temp_ws)
        self.assertFalse(ok)

    def test_workspace_command_filter(self):
        # Разрешенные команды
        allowed_cmds = [
            "python script.py",
            "git status",
            "ls -la",
            "mkdir -p src",
            "cat output.txt",
            "pytest tests/",
            "npm test",
        ]
        for cmd in allowed_cmds:
            safe, reason = gateway.is_safe_workspace_command(cmd)
            self.assertTrue(safe, f"Безопасная команда '{cmd}' была заблокирована: {reason}")

        # Запрещенные команды
        forbidden_cmds = [
            ("pkg install python", "pkg"),
            ("apt-get update", "apt"),
            ("sudo rm -rf .", "sudo"),
            ("reboot", "reboot"),
            ("cat ../../secret.txt", "relative traversal"),
            ("cat ..; ls", "relative traversal with semicolon"),
            ("cat ..|grep secret", "relative traversal with pipe"),
            ("cat /data/data/com.termux/files/home/.bashrc", "absolute path to /data"),
            ("cat $PREFIX/etc/apt/sources.list", "access to $PREFIX"),
            ("ls /sdcard/DCIM", "absolute path to /sdcard"),
            ("kill -9 123", "kill"),
            ("cat ~/.ssh/id_rsa", "home dotfiles"),
        ]
        for cmd, label in forbidden_cmds:
            safe, reason = gateway.is_safe_workspace_command(cmd)
            self.assertFalse(safe, f"Опасная команда '{cmd}' ({label}) не была заблокирована!")

    def test_tail_log_sensitive_protection(self):
        """Проверка блокировки доступа к приватным ключам и конфигам в tail_log."""
        # Блокировка SSH ключей
        res1 = gateway.read_tail_log("~/.ssh/id_rsa")
        self.assertIn("запрещен", res1)

        # Блокировка .env файла конфигурации
        res2 = gateway.read_tail_log("/data/data/com.termux/files/home/.termux_agent_gateway.env")
        self.assertIn("запрещен", res2)

    def test_resolve_cwd(self):
        """Проверка корректного разрешения рабочих каталогов с ~ и $HOME."""
        # None/пустая строка
        self.assertIsNone(gateway.resolve_cwd(None))
        self.assertIsNone(gateway.resolve_cwd(""))

        # Существующая папка через temp
        self.assertEqual(gateway.resolve_cwd(self.temp_ws), os.path.realpath(self.temp_ws))

        # Несуществующая папка
        self.assertIsNone(gateway.resolve_cwd(os.path.join(self.temp_ws, "nonexistent_12345")))


if __name__ == "__main__":
    unittest.main()
