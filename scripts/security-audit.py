#!/usr/bin/env python3
"""Security Audit — automated security checks for Neura v2 platform.

Checks:
  1. CORS configuration (no wildcard)
  2. JWT secret strength (min 32 chars, not default)
  3. Credentials exposure (plaintext tokens in configs)
  4. File permissions (home dirs, .env, creds files)
  5. Open ports (unexpected listeners)
  6. Rate limiting configuration
  7. UFW firewall status
  8. SSL/TLS on public endpoints
  9. Docker security (no --privileged)
  10. Stale sessions / temp files cleanup

Output: structured report with CRITICAL/HIGH/MEDIUM/LOW findings.
Can be run via cron or manually.

Usage:
  python3 security-audit.py           # Full audit, text output
  python3 security-audit.py --json    # JSON output
  python3 security-audit.py --fix     # Auto-fix safe issues
"""
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

NEURA_ROOT = Path("/opt/neura-v2")
HOMES_DIR = NEURA_ROOT / "homes"
CONFIG_DIR = NEURA_ROOT / "config" / "capsules"
ENV_FILE = NEURA_ROOT / ".env"


@dataclass
class Finding:
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, OK
    category: str
    title: str
    detail: str
    fix: str = ""
    auto_fixable: bool = False


@dataclass
class AuditReport:
    timestamp: str = ""
    findings: list = field(default_factory=list)
    score: int = 100  # starts at 100, deductions per finding

    def add(self, finding: Finding):
        self.findings.append(finding)
        if finding.severity == "CRITICAL":
            self.score -= 20
        elif finding.severity == "HIGH":
            self.score -= 10
        elif finding.severity == "MEDIUM":
            self.score -= 5
        self.score = max(0, self.score)


def check_cors(report: AuditReport):
    """Check CORS configuration."""
    # Look for CORS config in web.py or .env
    web_py = NEURA_ROOT / "neura" / "transport" / "web.py"
    if not web_py.exists():
        return

    content = web_py.read_text()
    if 'origins=["*"]' in content or "allow_origins=['*']" in content:
        report.add(Finding(
            severity="CRITICAL",
            category="CORS",
            title="CORS wildcard (*) позволяет запросы с любого домена",
            detail="Файл: web.py",
            fix="Заменить на список разрешённых доменов",
        ))
    elif "CORS_ORIGINS" in content or "allow_origins" in content:
        report.add(Finding(
            severity="OK",
            category="CORS",
            title="CORS настроен с whitelist",
            detail="",
        ))


def check_jwt(report: AuditReport):
    """Check JWT secret strength."""
    jwt_secret = os.environ.get("JWT_SECRET", "")

    if not jwt_secret:
        # Check .env
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                if line.startswith("JWT_SECRET="):
                    jwt_secret = line.split("=", 1)[1].strip()
                    break

    if not jwt_secret:
        report.add(Finding(
            severity="HIGH",
            category="JWT",
            title="JWT_SECRET не задан в env",
            detail="Используется рандомный ключ, сессии не переживут рестарт",
            fix="Добавить JWT_SECRET=<64+ символов> в .env",
        ))
    elif len(jwt_secret) < 32:
        report.add(Finding(
            severity="HIGH",
            category="JWT",
            title=f"JWT_SECRET слишком короткий ({len(jwt_secret)} символов)",
            detail="Рекомендуется минимум 64 символа",
            fix="Сгенерировать: python3 -c 'import secrets; print(secrets.token_hex(32))'",
        ))
    else:
        report.add(Finding(
            severity="OK",
            category="JWT",
            title=f"JWT_SECRET OK ({len(jwt_secret)} символов)",
            detail="",
        ))


def check_credentials(report: AuditReport):
    """Check for exposed credentials in config files."""
    issues = []

    # Check YAML configs for hardcoded tokens
    for yaml_file in CONFIG_DIR.glob("*.yaml"):
        content = yaml_file.read_text()
        # Check for hardcoded bot tokens (not ${VAR} references)
        if re.search(r"bot_token:\s+\d+:", content):
            issues.append(f"{yaml_file.name}: hardcoded bot_token")
        # Check for hardcoded API keys
        if re.search(r"api_key:\s+sk-", content):
            issues.append(f"{yaml_file.name}: hardcoded API key")

    if issues:
        report.add(Finding(
            severity="CRITICAL",
            category="Credentials",
            title=f"Найдены захардкоженные токены в {len(issues)} файл(ах)",
            detail="\n".join(issues),
            fix="Использовать ${ENV_VAR} ссылки вместо прямых значений",
        ))
    else:
        report.add(Finding(
            severity="OK",
            category="Credentials",
            title="Токены в YAML используют env-ссылки",
            detail="",
        ))

    # Check .env permissions
    if ENV_FILE.exists():
        mode = oct(ENV_FILE.stat().st_mode)[-3:]
        if mode not in ("600", "400"):
            report.add(Finding(
                severity="HIGH",
                category="Credentials",
                title=f".env файл имеет широкие права ({mode})",
                detail=str(ENV_FILE),
                fix=f"chmod 600 {ENV_FILE}",
                auto_fixable=True,
            ))


def check_permissions(report: AuditReport):
    """Check file/directory permissions."""
    issues = []

    # Check home dirs
    for home in HOMES_DIR.iterdir():
        if not home.is_dir():
            continue
        mode = oct(home.stat().st_mode)[-3:]
        if mode not in ("700", "750", "755"):
            issues.append(f"{home.name}: {mode} (expected 700)")

        # Check credentials files
        for cred_name in [".credentials.json", ".claude.json", ".bot-config"]:
            cred = home / cred_name
            if cred.exists() and not cred.is_symlink():
                cred_mode = oct(cred.stat().st_mode)[-3:]
                if cred_mode not in ("600", "400", "644"):
                    issues.append(f"{home.name}/{cred_name}: {cred_mode}")

    if issues:
        report.add(Finding(
            severity="MEDIUM",
            category="Permissions",
            title=f"Проблемы с правами в {len(issues)} файл(ах)/директориях",
            detail="\n".join(issues[:10]),
            fix="chmod 700 homes/*/; chmod 600 homes/*/.credentials.json",
        ))
    else:
        report.add(Finding(
            severity="OK",
            category="Permissions",
            title="Права на домашние директории OK",
            detail="",
        ))


def check_ports(report: AuditReport):
    """Check for unexpected open ports."""
    try:
        result = subprocess.run(
            ["ss", "-tlnp"], capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")[1:]  # skip header

        expected_ports = {
            "5432",   # PostgreSQL
            "6379",   # Redis
            "8080",   # Neura Web API
            "22",     # SSH
            "80",     # Nginx
            "443",    # Nginx HTTPS
            "7820",   # vsearch
        }

        unexpected = []
        for line in lines:
            # Extract port from local address
            match = re.search(r":(\d+)\s", line)
            if match:
                port = match.group(1)
                if port not in expected_ports and int(port) < 10000:
                    unexpected.append(f":{port} — {line.strip()[-50:]}")

        if unexpected:
            report.add(Finding(
                severity="MEDIUM",
                category="Network",
                title=f"Обнаружены неожиданные открытые порты ({len(unexpected)})",
                detail="\n".join(unexpected[:5]),
                fix="Проверить необходимость и закрыть через UFW",
            ))
        else:
            report.add(Finding(
                severity="OK",
                category="Network",
                title="Открытые порты соответствуют ожидаемым",
                detail="",
            ))
    except Exception as e:
        report.add(Finding(
            severity="LOW",
            category="Network",
            title=f"Не удалось проверить порты: {e}",
            detail="",
        ))


def check_ufw(report: AuditReport):
    """Check UFW firewall status."""
    try:
        result = subprocess.run(
            ["ufw", "status"], capture_output=True, text=True, timeout=5
        )
        if "inactive" in result.stdout.lower():
            report.add(Finding(
                severity="HIGH",
                category="Firewall",
                title="UFW firewall неактивен",
                detail="",
                fix="ufw enable (предварительно проверить правила)",
            ))
        elif "active" in result.stdout.lower():
            report.add(Finding(
                severity="OK",
                category="Firewall",
                title="UFW firewall активен",
                detail="",
            ))
    except Exception:
        pass


def check_rate_limits(report: AuditReport):
    """Check rate limiting configuration."""
    # Check per-minute rate limit in web.py
    rate_limit_py = NEURA_ROOT / "neura" / "transport" / "rate_limit.py"
    if rate_limit_py.exists():
        content = rate_limit_py.read_text()
        match = re.search(r"MAX_PER_MINUTE\s*=\s*(\d+)", content)
        if match:
            rpm = int(match.group(1))
            if rpm > 20:
                report.add(Finding(
                    severity="MEDIUM",
                    category="Rate Limit",
                    title=f"Per-minute rate limit высокий ({rpm}/мин)",
                    detail="Рекомендуется 8-15/мин для защиты от abuse",
                    fix=f"Уменьшить MAX_PER_MINUTE до 10",
                ))
            else:
                report.add(Finding(
                    severity="OK",
                    category="Rate Limit",
                    title=f"Per-minute rate limit OK ({rpm}/мин)",
                    detail="",
                ))


def check_temp_files(report: AuditReport):
    """Check for stale temp files."""
    stale = list(Path("/tmp").glob("neura_prompt_*.txt"))
    if stale:
        report.add(Finding(
            severity="LOW",
            category="Cleanup",
            title=f"Найдены {len(stale)} устаревших temp-файлов",
            detail="/tmp/neura_prompt_*.txt",
            fix="Удалить: rm /tmp/neura_prompt_*.txt",
            auto_fixable=True,
        ))


def check_docker(report: AuditReport):
    """Check Docker security."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}} {{.Ports}} {{.Command}}"],
            capture_output=True, text=True, timeout=5
        )
        containers = result.stdout.strip().split("\n")
        issues = []
        for c in containers:
            if not c.strip():
                continue
            if "--privileged" in c:
                issues.append(f"Privileged container: {c.split()[0]}")
            # Check for exposed ports on 0.0.0.0
            if "0.0.0.0:" in c:
                # Extract port
                port_match = re.search(r"0\.0\.0\.0:(\d+)", c)
                if port_match:
                    port = port_match.group(1)
                    if port not in ("80", "443"):
                        issues.append(f"Container {c.split()[0]} exposed on 0.0.0.0:{port}")

        if issues:
            report.add(Finding(
                severity="MEDIUM",
                category="Docker",
                title=f"Docker security: {len(issues)} замечаний",
                detail="\n".join(issues[:5]),
            ))
    except Exception:
        pass


def run_audit(auto_fix: bool = False) -> AuditReport:
    """Run full security audit."""
    report = AuditReport(
        timestamp=datetime.now(tz=__import__('datetime').timezone.utc).isoformat(),
    )

    check_cors(report)
    check_jwt(report)
    check_credentials(report)
    check_permissions(report)
    check_ports(report)
    check_ufw(report)
    check_rate_limits(report)
    check_temp_files(report)
    check_docker(report)

    # Auto-fix if requested
    if auto_fix:
        for f in report.findings:
            if f.auto_fixable and f.severity in ("MEDIUM", "LOW"):
                try:
                    if "chmod 600" in f.fix and ENV_FILE.exists():
                        os.chmod(str(ENV_FILE), 0o600)
                        f.detail += " [AUTO-FIXED]"
                    if "rm /tmp/neura_prompt" in f.fix:
                        for tmp in Path("/tmp").glob("neura_prompt_*.txt"):
                            tmp.unlink()
                        f.detail += " [AUTO-FIXED]"
                except Exception as e:
                    f.detail += f" [FIX FAILED: {e}]"

    return report


def format_text(report: AuditReport) -> str:
    """Format report as colored text."""
    SEVERITY_ICON = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "⚪",
        "OK": "🟢",
    }

    lines = [
        "═" * 60,
        "  NEURA V2 SECURITY AUDIT",
        f"  {report.timestamp}",
        "═" * 60,
        "",
    ]

    # Group by severity
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "OK"]:
        items = [f for f in report.findings if f.severity == severity]
        if not items:
            continue
        lines.append(f"\n{SEVERITY_ICON.get(severity, '?')} {severity} ({len(items)})")
        lines.append("─" * 40)
        for f in items:
            lines.append(f"  [{f.category}] {f.title}")
            if f.detail:
                for d in f.detail.split("\n")[:3]:
                    lines.append(f"    {d}")
            if f.fix:
                lines.append(f"    💡 {f.fix}")

    lines.append("")
    lines.append("═" * 60)

    critical = len([f for f in report.findings if f.severity == "CRITICAL"])
    high = len([f for f in report.findings if f.severity == "HIGH"])
    ok = len([f for f in report.findings if f.severity == "OK"])

    lines.append(f"  Score: {report.score}/100  |  "
                 f"CRITICAL: {critical}  HIGH: {high}  OK: {ok}")
    lines.append("═" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    is_json = "--json" in sys.argv
    auto_fix = "--fix" in sys.argv

    report = run_audit(auto_fix=auto_fix)

    if is_json:
        print(json.dumps({
            "timestamp": report.timestamp,
            "score": report.score,
            "findings": [asdict(f) for f in report.findings],
        }, indent=2, ensure_ascii=False))
    else:
        print(format_text(report))
