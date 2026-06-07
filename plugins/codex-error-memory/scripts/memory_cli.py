#!/usr/bin/env python3
"""SQLite-backed technical error memory for Codex plugins."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PLUGIN_ROOT / "data" / "error_memory.sqlite"

TOKEN_RE = re.compile(r"(?i)(bearer\s+)[a-z0-9._\-]{16,}")
SECRET_RE = re.compile(r"(?i)(password|passwd|secret|token|key)\s*[:=]\s*[^,\s;]+")
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b1[3-9]\d{9}\b")
OPENID_RE = re.compile(r"\bo[A-Za-z0-9_-]{20,}\b")
LONG_HEX_RE = re.compile(r"\b[a-fA-F0-9]{32,}\b")

WORD_RE = re.compile(r"[A-Za-z0-9_.$:/\\-]+|[\u4e00-\u9fff]{2,}")


BUILTIN_MEMORIES = [
    {
        "title": "PowerShell 中误用 Bash heredoc",
        "category": "shell",
        "severity": "medium",
        "signature": "python - <<'PY' Missing file specification after redirection operator",
        "keywords": "powershell bash heredoc python redirection",
        "root_cause": "PowerShell 不支持 Bash heredoc。`<<` 会被当成重定向符号解析。",
        "fix_steps": "改用 PowerShell here-string：@' ... '@ | python -，或写临时脚本文件执行。",
        "prevention_rule": "在 PowerShell 中不要使用 `python - <<'PY'`、`cat <<EOF` 等 Bash 写法。",
        "verification_steps": "重新运行命令，确认不再出现 Missing file specification 或 '<' operator 错误。",
        "files_often_involved": "PowerShell commands, scripts",
        "commands_often_used": "@'\\nprint(\"ok\")\\n'@ | python -",
    },
    {
        "title": "WXSS 或配置文件被 UTF-8 BOM 破坏",
        "category": "encoding",
        "severity": "high",
        "signature": "WXSS 文件编译错误 unexpected � at pos 1",
        "keywords": "wxss bom utf-8 unexpected pos 1",
        "root_cause": "文件开头含 UTF-8 BOM，微信开发工具或配置读取把隐藏字节当成非法字符。",
        "fix_steps": "用无 BOM UTF-8 重写文件，并检查 `.wxss`、`.wxml`、`.js`、`.json`、`.env`。",
        "prevention_rule": "不要用会写 BOM 的重定向或旧 Set-Content 写小程序源码。",
        "verification_steps": "重新编译小程序，确认不再出现 unexpected 字符错误。",
        "files_often_involved": "*.wxss, *.wxml, *.json, .env",
        "commands_often_used": "python scripts/check_windows_artifacts.py <path> --release --strict",
    },
    {
        "title": "发布包混入 localhost 或 127.0.0.1",
        "category": "release",
        "severity": "high",
        "signature": "ERR_CONNECTION_REFUSED 127.0.0.1 localhost",
        "keywords": "localhost 127.0.0.1 release err_connection_refused api asset",
        "root_cause": "本地开发地址进入了正式发布包或缓存 URL 没有转换为正式域名。",
        "fix_steps": "把 API/资源地址改为正式域名，必要时对旧缓存本地资源 URL 做正式域名映射。",
        "prevention_rule": "前端审核或上传前扫描发布包中的 localhost、127.0.0.1、测试端口。",
        "verification_steps": "发布包扫描无本地地址；开发工具网络请求只访问正式 API。",
        "files_often_involved": "miniprogram/app.js, config files",
        "commands_often_used": "python scripts/check_windows_artifacts.py <release> --release --strict",
    },
    {
        "title": "发布版本混入 pycache、数据库或日志",
        "category": "release",
        "severity": "high",
        "signature": "__pycache__ .pyc .db .sqlite .log in release artifact",
        "keywords": "pycache pyc db sqlite log release artifact github",
        "root_cause": "在发布目录里运行测试或服务，生成的运行文件被一起提交或上传。",
        "fix_steps": "删除 `__pycache__`、`.pyc`、`.db`、`.log`、临时密码文件；测试尽量不要在发布包目录运行。",
        "prevention_rule": "提交前运行发布包扫描，并保持 `.gitignore` 覆盖生成物。",
        "verification_steps": "扫描结果 0 error；git status 不包含生成文件。",
        "files_often_involved": "release folders, server/",
        "commands_often_used": "Get-ChildItem -Recurse -Directory -Filter __pycache__",
    },
    {
        "title": ".env 首个配置键被 BOM 污染",
        "category": "config",
        "severity": "high",
        "signature": "\\ufeff key missing env bom login stuck config missing",
        "keywords": "env bom config missing login stuck",
        "root_cause": "`.env` 文件开头含 BOM，首个 key 实际变成 `\\ufeffKEY`，导致配置读取失败。",
        "fix_steps": "用无 BOM UTF-8 重写 `.env`，诊断时打印配置 key 名但不要打印 secret。",
        "prevention_rule": "配置文件写入必须明确无 BOM，并在启动诊断中检查关键配置是否存在。",
        "verification_steps": "服务重启后关键配置能被读取，登录或 API 恢复正常。",
        "files_often_involved": ".env, config.py",
        "commands_often_used": "python -c \"from pathlib import Path; print(Path('.env').read_bytes()[:3])\"",
    },
    {
        "title": "Windows SSH 或 Paramiko 命令引号失控",
        "category": "deploy",
        "severity": "medium",
        "signature": "paramiko windows ssh quoting gbk utf-8 command failed",
        "keywords": "paramiko ssh windows quote gbk utf-8 powershell cmd",
        "root_cause": "远程 Windows 命令经过 Python、SSH、cmd/PowerShell 多层解析，特殊字符和编码容易变形。",
        "fix_steps": "上传临时 `.py`、`.ps1` 或 `.bat` 文件执行；输出按 UTF-8/GBK 防御性解码。",
        "prevention_rule": "复杂远程操作不要写成长 `exec_command` 字符串。",
        "verification_steps": "远程脚本执行成功，stdout/stderr 可读，临时文件被删除。",
        "files_often_involved": "deployment scripts, ssh helpers",
        "commands_often_used": "sftp put temp script; ssh exec python temp.py",
    },
    {
        "title": "Windows 计划任务 Last Result 异常",
        "category": "deploy",
        "severity": "medium",
        "signature": "Task Scheduler Last Result 255 exit code batch completed",
        "keywords": "scheduled task last result 255 bat exit code log",
        "root_cause": "bat 或 Python 包装脚本没有明确规范退出码，日志完成但任务结果显示异常。",
        "fix_steps": "bat 中记录开始/结束；失败 `exit /b 1`，成功明确 `exit /b 0`。",
        "prevention_rule": "所有计划任务入口都要有明确退出码和可读日志。",
        "verification_steps": "手动运行任务后 Last Result 为 0，日志有完成时间。",
        "files_often_involved": "*.bat, scheduled task scripts",
        "commands_often_used": "exit /b 0",
    },
    {
        "title": "Flask development server 直接暴露公网",
        "category": "deploy",
        "severity": "high",
        "signature": "Flask development server public 443 external scans",
        "keywords": "flask development server 443 production nginx waitress scans",
        "root_cause": "Flask 自带开发服务器直接承担正式公网入口，容易被外部扫描和异常请求拖住。",
        "fix_steps": "用 Nginx/Caddy 作为公网入口，Python 后端运行在本机端口的 Waitress/WSGI 后面。",
        "prevention_rule": "正式环境不要让 Flask dev server 直接监听公网 443。",
        "verification_steps": "公网只暴露 Nginx/Caddy；Python 服务只监听 127.0.0.1。",
        "files_often_involved": "deploy configs, server startup scripts",
        "commands_often_used": "netstat -ano | findstr :443",
    },
    {
        "title": "GitHub tag 与版本文件夹结构不一致",
        "category": "git",
        "severity": "medium",
        "signature": "tag version folder structure inconsistent old labels",
        "keywords": "github tag version folder archive structure old labels",
        "root_cause": "版本 tag 指向的提交和版本目录内容没有同步，或复制归档时保留旧版本标记。",
        "fix_steps": "统一版本目录、README、tag 指向的提交；必要时 force-update 版本 tag。",
        "prevention_rule": "推送前检查 `git log --decorate`、版本 README 和 `versions/<version>`。",
        "verification_steps": "GitHub tag 页面显示新提交，版本文件夹和说明一致。",
        "files_often_involved": "versions/, README.md",
        "commands_often_used": "git tag -f <version>; git push origin <version> --force",
    },
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sanitize(text: str) -> str:
    text = TOKEN_RE.sub(r"\1[REDACTED]", text)
    text = SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    text = OPENID_RE.sub("[OPENID]", text)
    text = LONG_HEX_RE.sub("[HEX]", text)
    return text[:4000]


def project_hash(path: str) -> str:
    normalized = str(Path(path).resolve()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            root_path_hash TEXT NOT NULL UNIQUE,
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS error_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT NOT NULL,
            signature TEXT NOT NULL,
            keywords TEXT NOT NULL DEFAULT '',
            stack_pattern TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'runtime',
            severity TEXT NOT NULL DEFAULT 'medium',
            confidence INTEGER NOT NULL DEFAULT 3,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS solutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id INTEGER NOT NULL,
            root_cause TEXT NOT NULL DEFAULT '',
            fix_steps TEXT NOT NULL DEFAULT '',
            prevention_rule TEXT NOT NULL DEFAULT '',
            verification_steps TEXT NOT NULL DEFAULT '',
            files_often_involved TEXT NOT NULL DEFAULT '',
            commands_often_used TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(pattern_id) REFERENCES error_patterns(id)
        );
        CREATE TABLE IF NOT EXISTS occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id INTEGER NOT NULL,
            raw_error_excerpt TEXT NOT NULL DEFAULT '',
            project_path TEXT NOT NULL DEFAULT '',
            resolved INTEGER NOT NULL DEFAULT 0,
            resolution_note TEXT NOT NULL DEFAULT '',
            occurred_at TEXT NOT NULL,
            FOREIGN KEY(pattern_id) REFERENCES error_patterns(id)
        );
        """
    )
    seed_builtin_memories(conn)
    conn.commit()


def seed_builtin_memories(conn: sqlite3.Connection) -> None:
    for item in BUILTIN_MEMORIES:
        exists = conn.execute(
            "SELECT id FROM error_patterns WHERE project_id IS NULL AND title = ?",
            (item["title"],),
        ).fetchone()
        if exists:
            continue
        ts = now()
        cur = conn.execute(
            """
            INSERT INTO error_patterns
            (project_id, title, signature, keywords, stack_pattern, category, severity, confidence, created_at, updated_at)
            VALUES (NULL, ?, ?, ?, '', ?, ?, 4, ?, ?)
            """,
            (item["title"], item["signature"], item["keywords"], item["category"], item["severity"], ts, ts),
        )
        conn.execute(
            """
            INSERT INTO solutions
            (pattern_id, root_cause, fix_steps, prevention_rule, verification_steps, files_often_involved, commands_often_used, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cur.lastrowid,
                item["root_cause"],
                item["fix_steps"],
                item["prevention_rule"],
                item["verification_steps"],
                item["files_often_involved"],
                item["commands_often_used"],
                ts,
                ts,
            ),
        )


def get_project(conn: sqlite3.Connection, project: str | None) -> int | None:
    if not project:
        return None
    path = Path(project).resolve()
    root_hash = project_hash(str(path))
    row = conn.execute("SELECT id FROM projects WHERE root_path_hash = ?", (root_hash,)).fetchone()
    if row:
        return int(row["id"])
    ts = now()
    cur = conn.execute(
        "INSERT INTO projects (name, root_path_hash, tags, created_at, updated_at) VALUES (?, ?, '', ?, ?)",
        (path.name or str(path), root_hash, ts, ts),
    )
    conn.commit()
    return int(cur.lastrowid)


def tokens(text: str) -> set[str]:
    return {item.lower() for item in WORD_RE.findall(text) if len(item.strip()) >= 2}


def score(text: str, row: sqlite3.Row) -> float:
    haystack = " ".join([row["title"], row["signature"], row["keywords"], row["stack_pattern"] or ""])
    query_tokens = tokens(text)
    memory_tokens = tokens(haystack)
    if not query_tokens or not memory_tokens:
        return 0.0
    overlap = len(query_tokens & memory_tokens)
    base = overlap / max(6, min(len(query_tokens), len(memory_tokens)))
    exact_bonus = 0.35 if row["signature"].lower() and row["signature"].lower() in text.lower() else 0.0
    confidence_bonus = min(int(row["confidence"]), 5) * 0.04
    return min(1.0, base + exact_bonus + confidence_bonus)


def read_text_arg(args: argparse.Namespace) -> str:
    if getattr(args, "file", None):
        return Path(args.file).read_text(encoding="utf-8", errors="replace")
    if getattr(args, "text", None):
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def command_search(args: argparse.Namespace) -> int:
    with connect(Path(args.db)) as conn:
        init_db(conn)
        project_id = get_project(conn, args.project)
        text = sanitize(read_text_arg(args))
        if not text.strip():
            print("No error text provided.")
            return 1
        rows = conn.execute(
            """
            SELECT p.*, s.root_cause, s.fix_steps, s.prevention_rule, s.verification_steps,
                   s.files_often_involved, s.commands_often_used
            FROM error_patterns p
            LEFT JOIN solutions s ON s.pattern_id = p.id
            WHERE p.project_id IS NULL OR p.project_id = ?
            """,
            (project_id,),
        ).fetchall()
        ranked = sorted(((score(text, row), row) for row in rows), key=lambda item: item[0], reverse=True)
        matches = [(value, row) for value, row in ranked if value >= args.min_score][: args.limit]
        if not matches:
            print(json.dumps({"matches": [], "message": "No strong memory match."}, ensure_ascii=False, indent=2))
            return 0
        payload = []
        for value, row in matches:
            payload.append(
                {
                    "score": round(value, 3),
                    "id": row["id"],
                    "title": row["title"],
                    "category": row["category"],
                    "severity": row["severity"],
                    "confidence": row["confidence"],
                    "root_cause": row["root_cause"] or "",
                    "fix_steps": row["fix_steps"] or "",
                    "prevention_rule": row["prevention_rule"] or "",
                    "verification_steps": row["verification_steps"] or "",
                    "files_often_involved": row["files_often_involved"] or "",
                    "commands_often_used": row["commands_often_used"] or "",
                }
            )
        print(json.dumps({"matches": payload}, ensure_ascii=False, indent=2))
        return 0


def command_add(args: argparse.Namespace) -> int:
    with connect(Path(args.db)) as conn:
        init_db(conn)
        project_id = get_project(conn, args.project)
        raw_error = sanitize(read_text_arg(args))
        signature = sanitize(args.signature or raw_error[:500] or args.title)
        ts = now()
        cur = conn.execute(
            """
            INSERT INTO error_patterns
            (project_id, title, signature, keywords, stack_pattern, category, severity, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                args.title,
                signature,
                args.keywords or "",
                args.stack_pattern or "",
                args.category,
                args.severity,
                args.confidence,
                ts,
                ts,
            ),
        )
        pattern_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO solutions
            (pattern_id, root_cause, fix_steps, prevention_rule, verification_steps, files_often_involved, commands_often_used, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pattern_id,
                args.root_cause or "",
                args.fix_steps or "",
                args.prevention_rule or "",
                args.verification_steps or "",
                args.files_often_involved or "",
                args.commands_often_used or "",
                ts,
                ts,
            ),
        )
        if raw_error:
            conn.execute(
                "INSERT INTO occurrences (pattern_id, raw_error_excerpt, project_path, resolved, resolution_note, occurred_at) VALUES (?, ?, ?, 1, ?, ?)",
                (pattern_id, raw_error[:1000], str(Path(args.project).resolve()) if args.project else "", "memory added", ts),
            )
        conn.commit()
        print(json.dumps({"added": True, "pattern_id": pattern_id}, ensure_ascii=False, indent=2))
        return 0


def command_record(args: argparse.Namespace) -> int:
    with connect(Path(args.db)) as conn:
        init_db(conn)
        raw_error = sanitize(read_text_arg(args))
        ts = now()
        conn.execute(
            "INSERT INTO occurrences (pattern_id, raw_error_excerpt, project_path, resolved, resolution_note, occurred_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                args.pattern_id,
                raw_error[:1000],
                str(Path(args.project).resolve()) if args.project else "",
                1 if args.resolved else 0,
                args.note or "",
                ts,
            ),
        )
        if args.resolved:
            conn.execute(
                "UPDATE error_patterns SET confidence = MIN(confidence + 1, 5), updated_at = ? WHERE id = ?",
                (ts, args.pattern_id),
            )
        conn.commit()
        print(json.dumps({"recorded": True, "pattern_id": args.pattern_id}, ensure_ascii=False, indent=2))
        return 0


def command_list(args: argparse.Namespace) -> int:
    with connect(Path(args.db)) as conn:
        init_db(conn)
        project_id = get_project(conn, args.project)
        rows = conn.execute(
            """
            SELECT id, title, category, severity, confidence, updated_at
            FROM error_patterns
            WHERE project_id IS NULL OR project_id = ?
            ORDER BY confidence DESC, updated_at DESC
            LIMIT ?
            """,
            (project_id, args.limit),
        ).fetchall()
        print(json.dumps({"memories": [dict(row) for row in rows]}, ensure_ascii=False, indent=2))
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex local technical error memory.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path.")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search prior error memories.")
    search.add_argument("--project", default="", help="Project root path.")
    search.add_argument("--text", default="", help="Error text.")
    search.add_argument("--file", default="", help="File containing error text.")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--min-score", type=float, default=0.18)
    search.set_defaults(func=command_search)

    add = sub.add_parser("add", help="Add a reusable technical error memory.")
    add.add_argument("--project", default="", help="Project root path.")
    add.add_argument("--title", required=True)
    add.add_argument("--text", default="", help="Error text.")
    add.add_argument("--file", default="", help="File containing error text.")
    add.add_argument("--signature", default="")
    add.add_argument("--keywords", default="")
    add.add_argument("--stack-pattern", default="")
    add.add_argument("--category", default="runtime")
    add.add_argument("--severity", default="medium")
    add.add_argument("--confidence", type=int, default=3)
    add.add_argument("--root-cause", default="")
    add.add_argument("--fix-steps", default="")
    add.add_argument("--prevention-rule", default="")
    add.add_argument("--verification-steps", default="")
    add.add_argument("--files-often-involved", default="")
    add.add_argument("--commands-often-used", default="")
    add.set_defaults(func=command_add)

    record = sub.add_parser("record", help="Record a repeated occurrence.")
    record.add_argument("--pattern-id", type=int, required=True)
    record.add_argument("--project", default="")
    record.add_argument("--text", default="")
    record.add_argument("--file", default="")
    record.add_argument("--resolved", action="store_true")
    record.add_argument("--note", default="")
    record.set_defaults(func=command_record)

    list_cmd = sub.add_parser("list", help="List known memories.")
    list_cmd.add_argument("--project", default="")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.set_defaults(func=command_list)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
