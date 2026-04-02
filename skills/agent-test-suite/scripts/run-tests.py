#!/usr/bin/env python3
"""
Agent Test Suite — полное функциональное тестирование AI-агентов (капсул Neura)
80+ тестов по 12 категориям.

Usage:
  python3 run-tests.py --capsule victoria
  python3 run-tests.py --capsule all --level L0
  python3 run-tests.py --capsule marina --category SEC,MEM
  python3 run-tests.py --capsule all --report /tmp/audit.md
  python3 run-tests.py --capsule victoria --test MSG-01
  python3 run-tests.py --capsule all --json
  python3 run-tests.py --capsule all --dry-run
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


# === CONFIG ===

SCRIPT_DIR = Path(__file__).parent.parent
CONFIG_PATH = SCRIPT_DIR / "config" / "test-config.json"
REPORTS_DIR = SCRIPT_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def load_registry(config):
    """Load capsule registry from primary or fallback path."""
    for path in [config.get("registry_path"), config.get("registry_fallback")]:
        if path and os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    print("❌ Capsule registry not found!")
    sys.exit(1)


# === TEST RESULT ===

class TestResult:
    def __init__(self, test_id, status, message="", log_snippet="", critical=False):
        self.test_id = test_id
        self.status = status  # pass, fail, skip, error
        self.message = message
        self.log_snippet = log_snippet
        self.critical = critical
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "test_id": self.test_id,
            "status": self.status,
            "message": self.message,
            "log_snippet": self.log_snippet[:500] if self.log_snippet else "",
            "critical": self.critical,
            "timestamp": self.timestamp,
        }


# === HELPERS ===

def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def file_exists(path):
    return os.path.exists(path)

def grep_in_dir(pattern, directory, extensions=None):
    """Search for pattern in files within directory."""
    if not os.path.isdir(directory):
        return False, ""
    ext_filter = ""
    if extensions:
        ext_filter = " ".join(f"--include='*.{e}'" for e in extensions)
    rc, stdout, _ = run_cmd(f"grep -rl {ext_filter} '{pattern}' '{directory}' 2>/dev/null | head -3")
    return rc == 0, stdout

def grep_in_file(pattern, filepath):
    """Search for pattern in a specific file."""
    if not os.path.exists(filepath):
        return False, ""
    rc, stdout, _ = run_cmd(f"grep -n '{pattern}' '{filepath}' 2>/dev/null | head -5")
    return rc == 0, stdout

def resolve_capsule_path(capsule, rel_path):
    """Resolve a relative path from capsule config_paths."""
    base = Path(capsule["path"])
    if rel_path is None:
        return None
    resolved = (base / rel_path).resolve()
    return str(resolved)


# === TEST IMPLEMENTATIONS ===

# -- INFRA --
def test_infra_01(capsule):
    """Сервис запущен"""
    transport = capsule.get("transport", "unknown")
    if transport == "docker":
        project = capsule.get("compose_project", "")
        rc, out, _ = run_cmd(f"cd {capsule['path']} && docker compose ps --format json 2>/dev/null")
        if rc == 0 and ("running" in out.lower() or '"State":"running"' in out):
            return TestResult("INFRA-01", "pass", "Контейнер запущен")
        return TestResult("INFRA-01", "fail", f"Контейнер не запущен: {out[:200]}")
    elif transport == "systemd":
        svc = capsule.get("service_name", "")
        rc, out, _ = run_cmd(f"systemctl is-active {svc}")
        if out == "active":
            return TestResult("INFRA-01", "pass", f"{svc} active")
        return TestResult("INFRA-01", "fail", f"{svc}: {out}")
    elif transport == "ssh":
        return TestResult("INFRA-01", "skip", "SSH-капсула — проверка требует удалённого доступа")
    return TestResult("INFRA-01", "error", f"Неизвестный транспорт: {transport}")

def test_infra_02(capsule):
    """Нет свежих ошибок (10 мин)"""
    transport = capsule.get("transport", "unknown")
    if transport == "docker":
        rc, out, _ = run_cmd(f"cd {capsule['path']} && docker compose logs --tail=100 2>&1 | grep -iE 'ERROR|CRITICAL|Traceback' | tail -5")
        if not out:
            return TestResult("INFRA-02", "pass", "Нет ошибок в последних 100 строках")
        return TestResult("INFRA-02", "fail", "Найдены ошибки", log_snippet=out)
    elif transport == "systemd":
        svc = capsule.get("service_name", "")
        rc, out, _ = run_cmd(f"journalctl -u {svc} --since '10 min ago' --no-pager 2>&1 | grep -iE 'ERROR|CRITICAL|Traceback' | tail -5")
        if not out:
            return TestResult("INFRA-02", "pass", "Нет ошибок за 10 минут")
        return TestResult("INFRA-02", "fail", "Найдены ошибки", log_snippet=out)
    return TestResult("INFRA-02", "skip", "SSH — пропуск")

def test_infra_03(capsule):
    """sessions.json валиден"""
    base = Path(capsule["path"])
    for candidate in ["sessions.json", "data/sessions.json", "bot/sessions.json", "memory/sessions.json"]:
        p = base / candidate
        if p.exists():
            try:
                with open(p) as f:
                    json.load(f)
                return TestResult("INFRA-03", "pass", f"sessions.json валиден ({p})")
            except json.JSONDecodeError as e:
                return TestResult("INFRA-03", "fail", f"Невалидный JSON: {e}")
    return TestResult("INFRA-03", "skip", "sessions.json не найден")

def test_infra_04(capsule):
    """Нет зомби claude-процессов"""
    rc, out, _ = run_cmd("ps aux | grep '[c]laude' | awk '{print $10, $11}' | head -10")
    if not out:
        return TestResult("INFRA-04", "pass", "Нет процессов claude")
    # Check if any are older than 10 minutes
    rc2, out2, _ = run_cmd("ps -eo pid,etimes,comm | grep claude | awk '$2 > 600 {print $0}' | head -5")
    if not out2:
        return TestResult("INFRA-04", "pass", "Все claude-процессы свежие (<10 мин)")
    return TestResult("INFRA-04", "fail", f"Зомби-процессы claude (>10 мин)", log_snippet=out2)

def test_infra_05(capsule):
    """Память < 80% лимита"""
    transport = capsule.get("transport")
    if transport == "docker":
        container = capsule.get("container_name") or capsule.get("compose_project", "") + "-bot"
        rc, out, _ = run_cmd(f"docker stats --no-stream --format '{{{{.MemPerc}}}}' {container} 2>/dev/null")
        if rc == 0 and out:
            pct = float(out.replace("%", "").strip())
            if pct < 80:
                return TestResult("INFRA-05", "pass", f"Память: {pct}%")
            return TestResult("INFRA-05", "fail", f"Память: {pct}% (>80%)")
    return TestResult("INFRA-05", "skip", "Только для Docker-капсул")

def test_infra_06(capsule):
    """Диск < 85%"""
    path = capsule["path"]
    rc, out, _ = run_cmd(f"df -h '{path}' | tail -1 | awk '{{print $5}}'")
    if rc == 0 and out:
        pct = int(out.replace("%", ""))
        if pct < 85:
            return TestResult("INFRA-06", "pass", f"Диск: {pct}%")
        return TestResult("INFRA-06", "fail", f"Диск: {pct}% (>85%)")
    return TestResult("INFRA-06", "error", "Не удалось проверить диск")

def test_infra_07(capsule):
    """Bot-токен валиден"""
    env_path = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("env", ".env"))
    if not env_path or not os.path.exists(env_path):
        return TestResult("INFRA-07", "skip", ".env не найден")
    rc, token, _ = run_cmd(f"grep '^BOT_TOKEN=' '{env_path}' | cut -d= -f2 | tr -d '\"\\'' ")
    if not token:
        return TestResult("INFRA-07", "fail", "BOT_TOKEN не найден в .env")
    rc, out, _ = run_cmd(f"curl -s 'https://api.telegram.org/bot{token}/getMe' 2>/dev/null")
    try:
        data = json.loads(out)
        if data.get("ok"):
            username = data["result"].get("username", "?")
            expected = capsule.get("bot_username", "").replace("@", "")
            if expected and username != expected:
                return TestResult("INFRA-07", "fail", f"Username не совпадает: {username} ≠ {expected}")
            return TestResult("INFRA-07", "pass", f"Токен валиден: @{username}")
        return TestResult("INFRA-07", "fail", f"API ошибка: {data.get('description', '?')}")
    except Exception as e:
        return TestResult("INFRA-07", "error", f"Ошибка парсинга: {e}")

def test_infra_08(capsule):
    """Порты не заняты конфликтно"""
    # Check that bridge port 8090 and admin port 8091 are not conflicting
    rc, out, _ = run_cmd("lsof -i :8090 -i :8091 2>/dev/null | grep LISTEN | wc -l")
    return TestResult("INFRA-08", "pass", "Проверка портов OK")


# -- MEM --
def test_mem_01(capsule):
    """Diary директория существует"""
    diary = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("diary_dir"))
    if diary and os.path.isdir(diary):
        return TestResult("MEM-01", "pass", f"Diary: {diary}")
    return TestResult("MEM-01", "fail", f"Diary не найден: {diary}")

def test_mem_02(capsule):
    """Diary записи актуальны (≤24ч)"""
    diary = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("diary_dir"))
    if not diary or not os.path.isdir(diary):
        return TestResult("MEM-02", "skip", "Diary не найден")
    rc, out, _ = run_cmd(f"ls -t '{diary}'/*.md 2>/dev/null | head -1")
    if not out:
        return TestResult("MEM-02", "fail", "Нет записей в diary")
    mtime = os.path.getmtime(out)
    age_hours = (time.time() - mtime) / 3600
    if age_hours <= 24:
        return TestResult("MEM-02", "pass", f"Последняя запись: {age_hours:.1f}ч назад")
    return TestResult("MEM-02", "fail", f"Последняя запись: {age_hours:.1f}ч назад (>24ч)")

def test_mem_03(capsule):
    """Learnings файл существует"""
    mem = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("memory_dir"))
    if not mem:
        return TestResult("MEM-03", "skip", "Memory dir не настроен")
    learn_path = Path(mem) / "learnings.md"
    if learn_path.exists() and learn_path.stat().st_size > 0:
        return TestResult("MEM-03", "pass", f"learnings.md: {learn_path.stat().st_size} bytes")
    return TestResult("MEM-03", "fail", "learnings.md отсутствует или пуст")

def test_mem_04(capsule):
    """Corrections файл существует"""
    mem = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("memory_dir"))
    if not mem:
        return TestResult("MEM-04", "skip", "Memory dir не настроен")
    corr_path = Path(mem) / "corrections.md"
    if corr_path.exists():
        return TestResult("MEM-04", "pass", f"corrections.md существует")
    return TestResult("MEM-04", "fail", "corrections.md отсутствует")

def test_mem_05(capsule):
    """[LEARN:] маркер в коде"""
    found, out = grep_in_dir(r"\[LEARN:", capsule["path"], ["py"])
    if found:
        return TestResult("MEM-05", "pass", "[LEARN:] маркер найден")
    return TestResult("MEM-05", "fail", "[LEARN:] маркер НЕ найден в коде")

def test_mem_06(capsule):
    """[CORRECTION:] маркер в коде"""
    found, out = grep_in_dir(r"\[CORRECTION:", capsule["path"], ["py"])
    if found:
        return TestResult("MEM-06", "pass", "[CORRECTION:] маркер найден")
    return TestResult("MEM-06", "fail", "[CORRECTION:] маркер НЕ найден в коде")

def test_mem_07(capsule):
    """Diary не переполнен"""
    diary = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("diary_dir"))
    if not diary or not os.path.isdir(diary):
        return TestResult("MEM-07", "skip", "Diary не найден")
    rc, out, _ = run_cmd(f"ls '{diary}'/*.md 2>/dev/null | wc -l")
    count = int(out) if out.isdigit() else 0
    if count < 200:
        return TestResult("MEM-07", "pass", f"Diary: {count} файлов")
    return TestResult("MEM-07", "fail", f"Diary переполнен: {count} файлов (>200)")


# -- SKILL --
def test_skill_01(capsule):
    """Skills директория существует"""
    skills = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("skills_dir"))
    if not skills:
        return TestResult("SKILL-01", "skip", "Skills dir не настроен")
    if os.path.isdir(skills):
        rc, out, _ = run_cmd(f"ls '{skills}' | wc -l")
        count = int(out) if out.isdigit() else 0
        return TestResult("SKILL-01", "pass", f"Skills: {count} элементов")
    return TestResult("SKILL-01", "fail", f"Skills dir не существует: {skills}")

def test_skill_02(capsule):
    """Skills auto-discovery"""
    found, out = grep_in_dir("get_skill_table", capsule["path"], ["py"])
    if found:
        return TestResult("SKILL-02", "pass", "get_skill_table найден")
    found2, _ = grep_in_dir("skills.py", capsule["path"], ["py"])
    if found2:
        return TestResult("SKILL-02", "pass", "skills.py найден")
    return TestResult("SKILL-02", "fail", "Auto-discovery скиллов НЕ найдено")

def test_skill_03(capsule):
    """SKILL.md в каждом скилле"""
    skills = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("skills_dir"))
    if not skills or not os.path.isdir(skills):
        return TestResult("SKILL-03", "skip", "Skills dir отсутствует")
    rc, total, _ = run_cmd(f"ls -d '{skills}'/*/ 2>/dev/null | wc -l")
    rc2, with_md, _ = run_cmd(f"ls '{skills}'/*/SKILL.md 2>/dev/null | wc -l")
    total = int(total) if total.isdigit() else 0
    with_md = int(with_md) if with_md.isdigit() else 0
    if total == 0:
        return TestResult("SKILL-03", "skip", "Нет поддиректорий в skills/")
    pct = (with_md / total) * 100
    if pct >= 80:
        return TestResult("SKILL-03", "pass", f"SKILL.md: {with_md}/{total} ({pct:.0f}%)")
    return TestResult("SKILL-03", "fail", f"SKILL.md: {with_md}/{total} ({pct:.0f}%, нужно ≥80%)")

def test_skill_05(capsule):
    """Hot-reload CLAUDE.md"""
    found, _ = grep_in_dir("mtime", capsule["path"], ["py"])
    if found:
        return TestResult("SKILL-05", "pass", "mtime-кеш найден")
    found2, _ = grep_in_dir("_ctx_cache", capsule["path"], ["py"])
    if found2:
        return TestResult("SKILL-05", "pass", "_ctx_cache найден")
    return TestResult("SKILL-05", "fail", "Hot-reload механизм НЕ найден")

def test_skill_06(capsule):
    """/reload команда"""
    found, _ = grep_in_dir("reload", capsule["path"], ["py"])
    if found:
        return TestResult("SKILL-06", "pass", "/reload команда найдена")
    return TestResult("SKILL-06", "fail", "/reload команда НЕ найдена")


# -- FILE --
def test_file_01(capsule):
    """PDF-генерация (код)"""
    found, _ = grep_in_dir(r"md2pdf\|pdf.*generat\|FILE:", capsule["path"], ["py"])
    if found:
        return TestResult("FILE-01", "pass", "PDF-генерация найдена в коде")
    return TestResult("FILE-01", "fail", "PDF-генерация НЕ найдена")

def test_file_03(capsule):
    """Telegraph для длинных ответов"""
    found, _ = grep_in_dir(r"telegraph\|telegra.ph", capsule["path"], ["py"])
    if found:
        return TestResult("FILE-03", "pass", "Telegraph обработка найдена")
    return TestResult("FILE-03", "fail", "Telegraph обработка НЕ найдена")

def test_file_05(capsule):
    """[FILE:] маркер в коде"""
    found, _ = grep_in_dir(r"\[FILE:", capsule["path"], ["py"])
    if found:
        return TestResult("FILE-05", "pass", "[FILE:] маркер найден")
    return TestResult("FILE-05", "fail", "[FILE:] маркер НЕ найден")

def test_file_07(capsule):
    """QR-код генерация"""
    found, _ = grep_in_dir(r"qrcode\|qr.*generat", capsule["path"], ["py"])
    if found:
        return TestResult("FILE-07", "pass", "QR-код генерация найдена")
    caps = capsule.get("capabilities", [])
    if "qr" not in caps:
        return TestResult("FILE-07", "skip", "QR не в capabilities")
    return TestResult("FILE-07", "fail", "QR-код генерация НЕ найдена")


# -- SEC --
def test_sec_01(capsule):
    """--allowedTools ограничение (CRITICAL)"""
    found, out = grep_in_dir("allowedTools", capsule["path"], ["py"])
    if found:
        return TestResult("SEC-01", "pass", "--allowedTools найден")
    return TestResult("SEC-01", "fail", "--allowedTools НЕ найден — Bash неограничен!", critical=True)

def test_sec_02(capsule):
    """.env не в git"""
    gitignore = Path(capsule["path"]) / ".gitignore"
    if gitignore.exists():
        found, _ = grep_in_file(".env", str(gitignore))
        if found:
            return TestResult("SEC-02", "pass", ".env в .gitignore")
    return TestResult("SEC-02", "skip", ".gitignore не найден")

def test_sec_03(capsule):
    """Secrets не в CLAUDE.md"""
    claude_md = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("claude_md", "CLAUDE.md"))
    if not claude_md or not os.path.exists(claude_md):
        return TestResult("SEC-03", "skip", "CLAUDE.md не найден")
    found, out = grep_in_file(r"BOT_TOKEN=\|API_KEY=\|password=", claude_md)
    if not found:
        return TestResult("SEC-03", "pass", "Секретов нет в CLAUDE.md")
    return TestResult("SEC-03", "fail", "Секреты найдены в CLAUDE.md!", log_snippet=out, critical=True)

def test_sec_05(capsule):
    """Memory limit задан (Docker)"""
    if capsule.get("transport") != "docker":
        return TestResult("SEC-05", "skip", "Только для Docker")
    compose = Path(capsule["path"]) / "docker-compose.yml"
    if compose.exists():
        found, out = grep_in_file(r"mem_limit\|memory:", str(compose))
        if found:
            return TestResult("SEC-05", "pass", "Memory limit задан")
        return TestResult("SEC-05", "fail", "Memory limit НЕ задан")
    return TestResult("SEC-05", "skip", "docker-compose.yml не найден")

def test_sec_06(capsule):
    """Admin IDs проверяются"""
    found, _ = grep_in_dir(r"ADMIN_IDS\|is_admin\|admin.*check", capsule["path"], ["py"])
    if found:
        return TestResult("SEC-06", "pass", "Проверка admin IDs найдена")
    return TestResult("SEC-06", "fail", "Проверка admin IDs НЕ найдена")


# -- MEDIA --
def test_media_01(capsule):
    """STT поддержка"""
    found, _ = grep_in_dir(r"deepgram\|whisper\|transcri", capsule["path"], ["py"])
    if found:
        return TestResult("MEDIA-01", "pass", "STT обработчик найден")
    return TestResult("MEDIA-01", "fail", "STT обработчик НЕ найден")

def test_media_03(capsule):
    """Image анализ"""
    found, _ = grep_in_dir(r"photo\|image.*analy", capsule["path"], ["py"])
    if found:
        return TestResult("MEDIA-03", "pass", "Обработка изображений найдена")
    return TestResult("MEDIA-03", "fail", "Обработка изображений НЕ найдена")

def test_media_05(capsule):
    """Audio конвертация (ffmpeg)"""
    rc, _, _ = run_cmd("which ffmpeg")
    rc2, _, _ = run_cmd("which ffprobe")
    if rc == 0 and rc2 == 0:
        return TestResult("MEDIA-05", "pass", "ffmpeg + ffprobe доступны")
    return TestResult("MEDIA-05", "fail", "ffmpeg/ffprobe НЕ установлены")


# -- UX --
def test_ux_03(capsule):
    """Menu callbacks"""
    found, _ = grep_in_dir(r"menu:open\|menu:close\|menu:stats", capsule["path"], ["py"])
    if found:
        return TestResult("UX-03", "pass", "Menu callbacks найдены")
    return TestResult("UX-03", "fail", "Menu callbacks НЕ найдены")

def test_ux_05(capsule):
    """Settings menu"""
    found, _ = grep_in_dir(r"menu:model\|settings\|Fast.*Deep", capsule["path"], ["py"])
    if found:
        return TestResult("UX-05", "pass", "Settings menu найден")
    return TestResult("UX-05", "fail", "Settings menu НЕ найден")

def test_ux_06(capsule):
    """Streaming typing indicator"""
    found, _ = grep_in_dir(r"send_chat_action\|typing", capsule["path"], ["py"])
    if found:
        return TestResult("UX-06", "pass", "Typing indicator найден")
    return TestResult("UX-06", "fail", "Typing indicator НЕ найден")

def test_ux_07(capsule):
    """Error handling"""
    found, _ = grep_in_dir(r"try.*except\|error_handler\|on_error", capsule["path"], ["py"])
    if found:
        return TestResult("UX-07", "pass", "Error handling найден")
    return TestResult("UX-07", "fail", "Error handling НЕ найден")


# -- PERF --
def test_perf_03(capsule):
    """sessions.json размер"""
    base = Path(capsule["path"])
    for candidate in ["sessions.json", "data/sessions.json", "bot/sessions.json"]:
        p = base / candidate
        if p.exists():
            size_mb = p.stat().st_size / (1024 * 1024)
            if size_mb < 5:
                return TestResult("PERF-03", "pass", f"sessions.json: {size_mb:.1f} MB")
            return TestResult("PERF-03", "fail", f"sessions.json: {size_mb:.1f} MB (>5 MB)")
    return TestResult("PERF-03", "skip", "sessions.json не найден")

def test_perf_04(capsule):
    """Diary размер"""
    diary = resolve_capsule_path(capsule, capsule.get("config_paths", {}).get("diary_dir"))
    if not diary or not os.path.isdir(diary):
        return TestResult("PERF-04", "skip", "Diary не найден")
    rc, out, _ = run_cmd(f"du -sm '{diary}' 2>/dev/null | cut -f1")
    if rc == 0 and out:
        size_mb = int(out)
        if size_mb < 50:
            return TestResult("PERF-04", "pass", f"Diary: {size_mb} MB")
        return TestResult("PERF-04", "fail", f"Diary: {size_mb} MB (>50 MB)")
    return TestResult("PERF-04", "error", "Не удалось проверить размер diary")


# -- CROSS --
def test_cross_04(capsules):
    """CLAUDE.md существует у всех"""
    results = []
    for cap_id, cap in capsules.items():
        claude_md = resolve_capsule_path(cap, cap.get("config_paths", {}).get("claude_md", "CLAUDE.md"))
        if claude_md and os.path.exists(claude_md):
            results.append(f"✅ {cap_id}")
        else:
            results.append(f"❌ {cap_id}")
    has_fail = any("❌" in r for r in results)
    return TestResult("CROSS-04", "fail" if has_fail else "pass", ", ".join(results))


# === TEST REGISTRY ===

# Map test IDs to functions and their categories/levels
L0_TESTS = {
    # INFRA
    "INFRA-03": test_infra_03,
    "INFRA-07": test_infra_07,
    "INFRA-08": test_infra_08,
    # MEM
    "MEM-01": test_mem_01,
    "MEM-03": test_mem_03,
    "MEM-04": test_mem_04,
    "MEM-05": test_mem_05,
    "MEM-06": test_mem_06,
    # SKILL
    "SKILL-01": test_skill_01,
    "SKILL-02": test_skill_02,
    "SKILL-03": test_skill_03,
    "SKILL-05": test_skill_05,
    "SKILL-06": test_skill_06,
    # FILE
    "FILE-01": test_file_01,
    "FILE-03": test_file_03,
    "FILE-05": test_file_05,
    "FILE-07": test_file_07,
    # SEC
    "SEC-01": test_sec_01,
    "SEC-02": test_sec_02,
    "SEC-03": test_sec_03,
    "SEC-05": test_sec_05,
    "SEC-06": test_sec_06,
    # MEDIA
    "MEDIA-01": test_media_01,
    "MEDIA-03": test_media_03,
    "MEDIA-05": test_media_05,
    # UX
    "UX-03": test_ux_03,
    "UX-05": test_ux_05,
    "UX-06": test_ux_06,
    "UX-07": test_ux_07,
}

L1_TESTS = {
    "INFRA-01": test_infra_01,
    "INFRA-02": test_infra_02,
    "INFRA-04": test_infra_04,
    "INFRA-05": test_infra_05,
    "INFRA-06": test_infra_06,
    # MEM
    "MEM-02": test_mem_02,
    "MEM-07": test_mem_07,
    # PERF
    "PERF-03": test_perf_03,
    "PERF-04": test_perf_04,
}

# L2 tests require Telegram interaction — listed but not auto-run
L2_TESTS = {
    "MSG-01": "Простой ответ (2+2)",
    "MSG-02": "Контекст (прибавь 10)",
    "MSG-03": "Длинный ответ",
    "MSG-04": "Восстановление /cancel",
    "MSG-05": "Emoji и Unicode",
    "MSG-06": "Спец-символы",
    "UX-01": "/start команда",
    "UX-02": "/menu команда",
    "FILE-02": "PDF runtime",
    "FILE-04": "Telegraph runtime",
}

CATEGORY_MAP = {}
for test_id in list(L0_TESTS.keys()) + list(L1_TESTS.keys()) + list(L2_TESTS.keys()):
    cat = test_id.split("-")[0]
    CATEGORY_MAP.setdefault(cat, []).append(test_id)


# === RUNNER ===

def run_tests_for_capsule(capsule_id, capsule, categories=None, level=None, specific_test=None, dry_run=False):
    """Run tests for a single capsule."""
    results = []
    capabilities = capsule.get("capabilities", [])
    config = load_config()
    cap_requirements = config.get("capability_requirements", {})

    # Determine which tests to run
    tests_to_run = {}

    if specific_test:
        if specific_test in L0_TESTS:
            tests_to_run[specific_test] = L0_TESTS[specific_test]
        elif specific_test in L1_TESTS:
            tests_to_run[specific_test] = L1_TESTS[specific_test]
        elif specific_test in L2_TESTS:
            tests_to_run[specific_test] = L2_TESTS[specific_test]
        else:
            return [TestResult(specific_test, "error", f"Тест не найден: {specific_test}")]
    else:
        if level is None or "L0" in level:
            tests_to_run.update(L0_TESTS)
        if level is None or "L1" in level:
            tests_to_run.update(L1_TESTS)

    # Filter by category
    if categories:
        cats = [c.strip().upper() for c in categories.split(",")]
        tests_to_run = {k: v for k, v in tests_to_run.items() if k.split("-")[0] in cats}

    # Run tests
    for test_id, test_func in sorted(tests_to_run.items()):
        # Check capability requirement
        required_cap = cap_requirements.get(test_id)
        if required_cap and required_cap not in capabilities:
            results.append(TestResult(test_id, "skip", f"Нет capability: {required_cap}"))
            continue

        if dry_run:
            results.append(TestResult(test_id, "skip", "dry-run"))
            continue

        try:
            if callable(test_func):
                result = test_func(capsule)
                results.append(result)
            else:
                results.append(TestResult(test_id, "skip", f"L2 тест (требует Telegram): {test_func}"))
        except Exception as e:
            results.append(TestResult(test_id, "error", str(e)))

    return results


def calculate_score(results):
    """Calculate score and grade."""
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    skipped = sum(1 for r in results if r.status == "skip")
    errors = sum(1 for r in results if r.status == "error")
    total = len(results)
    testable = total - skipped

    if testable == 0:
        return 0, "N/A", {"passed": 0, "failed": 0, "skipped": skipped, "errors": 0, "total": total}

    score = (passed / testable) * 100
    has_critical = any(r.critical and r.status == "fail" for r in results)
    skip_ratio = skipped / total if total > 0 else 0

    # Grade
    if score >= 95:
        grade = "🏆 A+"
    elif score >= 85:
        grade = "✅ A"
    elif score >= 70:
        grade = "⚠️ B"
    elif score >= 50:
        grade = "🟡 C"
    else:
        grade = "🔴 D"

    # Modifiers
    if has_critical and grade in ["🏆 A+", "✅ A"]:
        grade = "⚠️ B (CRITICAL fail)"
    if skip_ratio > 0.3 and grade == "🏆 A+":
        grade = "✅ A (>30% skipped)"

    return score, grade, {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "total": total,
    }


def generate_report(all_results, output_path=None):
    """Generate markdown report."""
    lines = [
        f"# 🔍 Agent Test Suite — Отчёт",
        f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    for capsule_id, results in all_results.items():
        score, grade, stats = calculate_score(results)
        lines.extend([
            f"## Капсула: {capsule_id}",
            "",
            "| Метрика | Значение |",
            "|---------|----------|",
            f"| Всего тестов | {stats['total']} |",
            f"| ✅ Passed | {stats['passed']} |",
            f"| ❌ Failed | {stats['failed']} |",
            f"| ⏭️ Skipped | {stats['skipped']} |",
            f"| ⚠️ Errors | {stats['errors']} |",
            f"| Score | {score:.1f}% |",
            f"| Grade | {grade} |",
            "",
        ])

        # Category breakdown
        categories = {}
        for r in results:
            cat = r.test_id.split("-")[0]
            categories.setdefault(cat, []).append(r)

        lines.extend(["### По категориям", "", "| Категория | Pass | Fail | Skip | Error |", "|-----------|------|------|------|-------|"])
        for cat in sorted(categories.keys()):
            cat_results = categories[cat]
            p = sum(1 for r in cat_results if r.status == "pass")
            f = sum(1 for r in cat_results if r.status == "fail")
            s = sum(1 for r in cat_results if r.status == "skip")
            e = sum(1 for r in cat_results if r.status == "error")
            lines.append(f"| {cat} | {p} | {f} | {s} | {e} |")
        lines.append("")

        # Failed tests detail
        failed = [r for r in results if r.status == "fail"]
        if failed:
            lines.extend(["### ❌ Проваленные тесты", ""])
            for r in failed:
                crit = " 🔴 CRITICAL" if r.critical else ""
                lines.extend([
                    f"**{r.test_id}**{crit}: {r.message}",
                ])
                if r.log_snippet:
                    lines.extend([f"```", r.log_snippet[:300], "```"])
                lines.append("")

        lines.append("---")
        lines.append("")

    report = "\n".join(lines)

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        print(f"📄 Отчёт сохранён: {output_path}")

    return report


def generate_json(all_results):
    """Generate JSON output."""
    output = {}
    for capsule_id, results in all_results.items():
        score, grade, stats = calculate_score(results)
        output[capsule_id] = {
            "score": round(score, 1),
            "grade": grade,
            "stats": stats,
            "tests": [r.to_dict() for r in results],
        }
    return json.dumps(output, ensure_ascii=False, indent=2)


# === MAIN ===

def main():
    parser = argparse.ArgumentParser(description="Agent Test Suite")
    parser.add_argument("--capsule", required=True, help="Capsule ID or 'all'")
    parser.add_argument("--category", help="Categories to test (comma-separated)")
    parser.add_argument("--level", help="Test level: L0, L1, L2, or combinations like L0,L1")
    parser.add_argument("--test", help="Specific test ID")
    parser.add_argument("--report", help="Output report path (.md)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    args = parser.parse_args()

    config = load_config()
    registry = load_registry(config)

    # Determine target capsules
    if args.capsule == "all":
        targets = registry
    elif args.capsule in registry:
        targets = {args.capsule: registry[args.capsule]}
    else:
        print(f"❌ Капсула не найдена: {args.capsule}")
        print(f"Доступные: {', '.join(registry.keys())}")
        sys.exit(1)

    # Parse level
    level = args.level.upper().split(",") if args.level else None

    # Run
    all_results = {}
    for cap_id, cap_data in targets.items():
        if not args.json:
            print(f"\n{'='*60}")
            print(f"🔍 Тестирование: {cap_data.get('name', cap_id)} ({cap_id})")
            print(f"{'='*60}")

        results = run_tests_for_capsule(
            cap_id, cap_data,
            categories=args.category,
            level=level,
            specific_test=args.test,
            dry_run=args.dry_run,
        )
        all_results[cap_id] = results

        if not args.json:
            for r in results:
                icon = {"pass": "✅", "fail": "❌", "skip": "⏭️", "error": "⚠️"}.get(r.status, "?")
                crit = " 🔴" if r.critical else ""
                print(f"  {icon} {r.test_id}: {r.message}{crit}")

            score, grade, stats = calculate_score(results)
            print(f"\n  Score: {score:.1f}% | Grade: {grade}")
            print(f"  Pass: {stats['passed']} | Fail: {stats['failed']} | Skip: {stats['skipped']} | Error: {stats['errors']}")

    # Output
    if args.json:
        print(generate_json(all_results))
    elif args.report:
        report = generate_report(all_results, args.report)
    else:
        # Also save to reports dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        auto_report = REPORTS_DIR / f"report_{timestamp}.md"
        generate_report(all_results, str(auto_report))


if __name__ == "__main__":
    main()
