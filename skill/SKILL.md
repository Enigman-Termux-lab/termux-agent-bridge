---
name: termux-agent-gateway
description: Универсальный MCP-шлюз для удалённого управления Android Termux из любых ИИ-агентов (OpenAI Codex, Claude Code, Google Antigravity, Gemini Spark, Cursor, Windsurf).
---

# 🚀 Termux Agent Gateway (MCP)

Этот навык перенесён и расширен до универсального шлюза:
Полная документация находится в [skills/termux-agent-gateway/SKILL.md](../skills/termux-agent-gateway/SKILL.md).

## Быстрый старт подключения:
- **OpenAI Codex:** Settings → MCP servers → Add server → Name: `Termux MCP Bridge`, Type: `Streamable HTTP`, URL: `https://<DOMAIN>/<SECRET_PATH>/sse`, Auth: `None`.
- **Claude Code:** `claude mcp add termux --transport http https://<DOMAIN>/<SECRET_PATH>/sse`
- **Gemini Spark:** Connected Apps → Custom apps for Spark → URL: `https://<DOMAIN>/<SECRET_PATH>/sse`
- **Google Antigravity:** Настройки MCP → URL: `https://<DOMAIN>/<SECRET_PATH>/sse`
