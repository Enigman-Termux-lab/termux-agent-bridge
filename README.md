# ⚡ Termux Antigravity Bridge (MCP) for Gemini Spark

Двусторонний защищённый мост по протоколу **Model Context Protocol (MCP)**, позволяющий веб-ассистенту **Gemini Spark** (на ПК или телефоне с подпиской Google One AI Premium / Gemini Pro) удалённо управлять терминалом **Termux на Android** и агентом **Antigravity CLI (`agy`)**.

---

## 🎯 Зачем это нужно

Связать облачный интерфейс Gemini Spark с вашей локальной машиной:
* Удалённо запускать системные команды в Termux (`bash_run`).
* Делегировать автономные задачи локальному агенту Antigravity CLI (`antigravity_run`).
* Мониторить состояние Android-устройства и батареи прямо из чата (`system_status`).

---

## 🔌 Как это работает (Схема подключения)

```text
[Gemini Spark (Web / App)]
         │
         │ Streamable HTTP (POST / GET)
         │ Режим: Authentication: None (Direct Secret Capability URL)
         ▼
[Ngrok Tunnel (*.ngrok-free.dev)]
         │
         │ Проброс секретного пути (/spark-sec-.../sse)
         │ через termux-chroot (фикс DNS Android)
         ▼
[Termux: agy_bridge.py (Python MCPServer + Uvicorn на порту 8000)]
         │
         ├──► agy CLI (Antigravity с флагом --dangerously-skip-permissions)
         └──► /data/data/com.termux/files/usr/bin/bash (git, gh, curl, fs)
```

1. В Termux стартует легковесный сервер `agy_bridge.py` на базе `mcp.server.MCPServer` и `uvicorn`.
2. Бинарник `ngrok` пробрасывает локальный порт `8000` в защищённый туннель с длинным секретным префиксом пути.
3. В настройках Gemini Spark (*Connected Apps → Custom apps for Spark*) указывается URL туннеля с типом аутентификации **None**.

---

## ⚠️ Специфика и ограничения Gemini Spark (Внимание!)

Перед использованием учитывайте архитектурные особенности агента Gemini Spark:

* **Отсутствие авто-подтверждения (No Auto-Approve):** Gemini Spark крайне зарегулирован политиками безопасности. На **каждый** вызов инструмента (`bash_run`, `antigravity_run`) в веб-интерфейсе требуется вручную нажимать кнопку подтверждения действия. Пакетного или полностью фонового выполнения без участия пользователя здесь нет.
* **Склонность к «забыванию» инструментов:** Модель в Spark деревянная и периодически игнорирует наличие кастомного MCP-моста, пытаясь выполнить команды в своей облачной песочнице, пока её явно не направить на использование подключённого моста.
* **Транспорт:** Требуется именно **Streamable HTTP** (`mcp.streamable_http_app()`), так как стандартный SSE падает с ошибкой HTTP 405 при инициализирующем POST-запросе от серверов Google.

---

## 🧠 Скилл для ИИ-агентов (Releases)

В разделе **[Releases](https://github.com/Enigman-Termux-lab/gemini-spark-mcp-bridge/releases)** прикреплён готовый архив скилла:
📦 **`gemini-spark-mcp-bridge-skill.zip`** (исходник также доступен в папке `skill/SKILL.md`).

Скилл обучает агентов Gemini Spark/Antigravity правильному протоколу работы с этим мостом:
* Как подключаться к Termux/ПК через подписку Gemini Pro.
* Как обходить ограничения модели (учитывать отсутствие авто-подтверждения и необходимость ручного аппрува tool-вызовов).
* Как правильно адресовать команды в Termux вместо внутренней облачной песочницы.

---

## 📁 Структура репозитория

* `gemini-spark-mcp-bridge.md` — исчерпывающий пошаговый гайд со всеми командами, фиксами DNS в Android, установкой ARM64 ngrok и настройкой Starlette/Uvicorn.
* `agy_bridge.py` — сервер моста на Python (MCPServer + Streamable HTTP + Uvicorn).
* `SparkMCP.sh` — готовый скрипт для Termux:Widget (запуск, перезапуск, копирование URL в буфер и остановка моста в один тап).
* `skill/SKILL.md` — файл навыка для ИИ-агентов.

---

#mcp #gemini-spark #antigravity #termux #android #ai-agents #streamable-http #ngrok #fastmcp #gemini-pro
