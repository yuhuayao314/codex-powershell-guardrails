#!/usr/bin/env python3
"""Scan Windows/Codex release artifacts for common footguns.

The scanner is intentionally conservative. It catches issues that are cheap to
miss during fast Codex work on Windows: UTF-8 BOMs, local API URLs, generated
runtime files, shell syntax that belongs to Bash, and release-only secrets.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".ts",
    ".wxml",
    ".wxss",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
}

RUNTIME_FILE_PATTERNS = [
    ".env",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.bak",
    "*.tmp",
]

LOCAL_PATTERNS = [
    re.compile(r"https?://(?:127\.0\.0\.1|localhost|0\.0\.0\.0)(?::\d+)?", re.I),
    re.compile(r"\b(?:127\.0\.0\.1|localhost|0\.0\.0\.0):\d+\b", re.I),
]

BASH_HEREDOC = re.compile(r"<<\s*['\"]?[A-Za-z_][A-Za-z0-9_]*['\"]?")
RISKY_CROSS_SHELL_DELETE = re.compile(r"\bcmd\s*/c\s+(?:del|rmdir|rd)\b", re.I)


@dataclass(frozen=True)
class Finding:
    level: str
    path: Path
    message: str
    line: int | None = None

    def render(self, root: Path | None = None) -> str:
        display = self.path
        if root:
            try:
                display = self.path.relative_to(root)
            except ValueError:
                pass
        suffix = f":{self.line}" if self.line else ""
        return f"{self.level}: {display}{suffix} - {self.message}"


def is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name.lower() in {".env", ".gitignore"}


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIRS


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for base in paths:
        if base.is_file():
            yield base
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            current = Path(dirpath)
            dirnames[:] = [d for d in dirnames if not should_skip_dir(current / d)]
            for name in filenames:
                yield current / name


def matches_any(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def scan_file(path: Path, *, release: bool, allow_localhost: bool) -> list[Finding]:
    findings: list[Finding] = []
    name = path.name
    lowered = name.lower()

    if path.parent.name == "__pycache__":
        findings.append(Finding("ERROR" if release else "WARN", path, "generated __pycache__ file should not be packaged"))

    if release and matches_any(lowered, RUNTIME_FILE_PATTERNS):
        findings.append(Finding("ERROR", path, "runtime, secret, database, log, or temporary file in release artifact"))

    if not is_text_candidate(path):
        return findings

    try:
        data = path.read_bytes()
    except OSError as exc:
        findings.append(Finding("WARN", path, f"could not read file: {exc}"))
        return findings

    if data.startswith(b"\xef\xbb\xbf"):
        findings.append(Finding("ERROR", path, "UTF-8 BOM detected; can break WXSS, .env, and source parsing"))

    if len(data) > 2_000_000:
        findings.append(Finding("WARN", path, "text candidate is larger than 2 MB; skipped content scan"))
        return findings

    text = data.decode("utf-8-sig", errors="replace")
    for index, line in enumerate(text.splitlines(), start=1):
        if not allow_localhost:
            for pattern in LOCAL_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding("ERROR" if release else "WARN", path, "local-only host or development port reference", index))
                    break

        if path.suffix.lower() in {".ps1", ".bat", ".cmd"} and BASH_HEREDOC.search(line):
            findings.append(Finding("WARN", path, "Bash heredoc syntax appears in Windows-oriented file", index))

        if path.suffix.lower() in {".ps1", ".bat", ".cmd"} and RISKY_CROSS_SHELL_DELETE.search(line):
            findings.append(Finding("WARN", path, "cross-shell delete command; prefer one shell with literal paths", index))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan Windows/Codex artifacts for release and PowerShell mistakes.")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan.")
    parser.add_argument("--release", action="store_true", help="Treat findings as release-blocking where appropriate.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero for warnings as well as errors.")
    parser.add_argument("--allow-localhost", action="store_true", help="Do not warn about localhost or 127.0.0.1 references.")
    args = parser.parse_args(argv)

    roots = [Path(item).resolve() for item in args.paths]
    findings: list[Finding] = []

    for root in roots:
        if not root.exists():
            findings.append(Finding("ERROR", root, "path does not exist"))
            continue
        for file_path in iter_files([root]):
            findings.extend(scan_file(file_path, release=args.release, allow_localhost=args.allow_localhost))

    base = roots[0] if len(roots) == 1 and roots[0].is_dir() else None
    for finding in findings:
        print(finding.render(base))

    errors = sum(1 for item in findings if item.level == "ERROR")
    warnings = sum(1 for item in findings if item.level == "WARN")
    print(f"Scan complete: {errors} error(s), {warnings} warning(s).")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
