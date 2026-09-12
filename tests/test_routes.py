"""
Тесты для проверки HTTP/SSE маршрутов и Capability URL.
"""

import unittest
from starlette.testclient import TestClient

import gateway


class TestGatewayRoutes(unittest.TestCase):
    def setUp(self):
        self.secret = "test-secret-12345"
        self.old_secret = "old-secret-67890"
        self.config = {
            "mode": "interactive",
            "port": 8000,
            "secret_path": self.secret,
            "old_secret_path": self.old_secret,
            "workspace_dir": "test_ws",
            "approval_timeout": 5,
            "ngrok_domain": "",
        }
        self.app, self.mcp = gateway.build_app(self.config)

    def test_routes_presence(self):
        route_paths = [r.path for r in self.app.routes if hasattr(r, "path")]
        # Проверяем наличие основного MCP пути
        self.assertIn(f"/{self.secret}/mcp", route_paths)
        # Проверяем алиасы для SSE
        self.assertIn(f"/{self.secret}", route_paths)
        self.assertIn(f"/{self.secret}/sse", route_paths)

        # Проверяем healthcheck
        self.assertIn("/health", route_paths)
        self.assertIn(f"/{self.secret}/health", route_paths)

        # Проверяем старый секретный путь
        self.assertIn(f"/{self.old_secret}", route_paths)
        self.assertIn(f"/{self.old_secret}/sse", route_paths)
        self.assertIn(f"/{self.old_secret}/mcp", route_paths)

    def test_health_check_endpoint(self):
        with TestClient(self.app) as client:
            resp = client.get("/health")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["gateway"], "Termux Agent Gateway")
            self.assertEqual(data["mode"], "interactive")
            self.assertIn("bash_run", data["tools"])

            # Тест с секретным путем
            resp_sec = client.get(f"/{self.secret}/health")
            self.assertEqual(resp_sec.status_code, 200)
            data_sec = resp_sec.json()
            self.assertEqual(data_sec["status"], "ok")


if __name__ == "__main__":
    unittest.main()
