"""
Тесты для проверки 4 профилей безопасности Termux Agent Gateway.
Проверяют корректность динамической регистрации инструментов MCP.
"""

import asyncio
import os
import unittest

import gateway


class TestSecurityProfiles(unittest.TestCase):
    def get_tool_names(self, mode: str) -> list[str]:
        config = {
            "mode": mode,
            "port": 8000,
            "secret_path": "test-secret",
            "old_secret_path": "",
            "workspace_dir": os.path.abspath("test_ws"),
            "approval_timeout": 5,
            "ngrok_domain": "",
        }
        server = gateway.create_gateway_server(config)
        tools = asyncio.run(server.list_tools())
        return [t.name for t in tools]

    def test_monitor_profile(self):
        """Профиль MONITOR: только чтение, никаких команд исполнения или изменения файлов."""
        tools = self.get_tool_names("monitor")
        self.assertIn("system_status", tools)
        self.assertIn("battery_info", tools)
        self.assertIn("tail_log", tools)

        # Никаких bash и изменений файлов быть не должно
        self.assertNotIn("bash_run", tools)
        self.assertNotIn("workspace_bash", tools)
        self.assertNotIn("antigravity_run", tools)
        self.assertNotIn("termux_api", tools)
        self.assertNotIn("file_read", tools)
        self.assertNotIn("file_write", tools)

    def test_workspace_profile(self):
        """Профиль WORKSPACE: изолированная песочница в ~/workspace."""
        tools = self.get_tool_names("workspace")
        self.assertIn("system_status", tools)
        self.assertIn("battery_info", tools)
        self.assertIn("tail_log", tools)
        self.assertIn("workspace_bash", tools)
        self.assertIn("file_read", tools)
        self.assertIn("file_write", tools)

        # Общий bash_run и godmode инструменты запрещены
        self.assertNotIn("bash_run", tools)
        self.assertNotIn("antigravity_run", tools)
        self.assertNotIn("termux_api", tools)

    def test_interactive_profile(self):
        """Профиль INTERACTIVE: стандартный bash с push-подтверждением опасных команд."""
        tools = self.get_tool_names("interactive")
        self.assertIn("system_status", tools)
        self.assertIn("battery_info", tools)
        self.assertIn("tail_log", tools)
        self.assertIn("bash_run", tools)

        # Специфичные для других режимов инструменты отсутствуют
        self.assertNotIn("workspace_bash", tools)
        self.assertNotIn("antigravity_run", tools)
        self.assertNotIn("termux_api", tools)

    def test_godmode_profile(self):
        """Профиль GODMODE: полный доступ, включая Antigravity CLI и Termux:API."""
        tools = self.get_tool_names("godmode")
        self.assertIn("system_status", tools)
        self.assertIn("battery_info", tools)
        self.assertIn("tail_log", tools)
        self.assertIn("bash_run", tools)
        self.assertIn("antigravity_run", tools)
        self.assertIn("termux_api", tools)


if __name__ == "__main__":
    unittest.main()
