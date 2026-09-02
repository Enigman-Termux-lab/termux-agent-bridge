---
name: gemini-spark-mcp-bridge
description: Подключение и управление Termux Antigravity Bridge (MCP) через Gemini Spark на ПК и телефоне (Gemini Pro).
---

# Gemini Spark MCP Bridge: Termux & Antigravity

Навык для ИИ-агентов по настройке и взаимодействию с Termux Antigravity Bridge из веб-интерфейса Gemini Spark (на ПК или Android с подпиской Gemini Pro / Google One AI Premium).

## Назначение
Позволяет веб-ассистенту Spark управлять локальным окружением Termux на Android:
- Исполнение bash-команд (`bash_run`).
- Запуск и продолжение сессий Antigravity CLI (`antigravity_run`).
- Мониторинг состояния телефона и батареи (`system_status`).

## Особенности и ограничения агента Gemini Spark
- **Отсутствие авто-подтверждения:** На каждый tool-call пользователю необходимо вручную нажимать кнопку подтверждения в веб-интерфейсе.
- **Склонность к галлюцинациям песочницы:** Spark часто путает свой облачный bash с локальным Termux и требует явного указания использовать инструменты моста.
- **Транспорт:** Строго Streamable HTTP (`POST`/`GET`), обычный SSE блокируется с HTTP 405.

## Протокол подключения
1. Запуск моста в Termux: `SparkMCP.sh` или `python ~/agy_bridge.py` + `termux-chroot ngrok http 8000 --url=...`.
2. Подключение в Gemini Spark: `Settings` -> `Connected Apps` -> `Custom apps for Spark` -> URL: `https://<NGROK_DOMAIN>/<SECRET_PATH>/sse`, `Authentication: None`.
