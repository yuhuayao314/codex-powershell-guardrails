#!/usr/bin/env python3
"""Extract a compact signature from a log or command output."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


NOISE = re.compile(r"^\s*(at |File \"|Traceback|During handling|={3,}|-{3,})")


def extract(text: str, limit: int) -> str:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "error" in line.lower() or "failed" in line.lower() or "exception" in line.lower() or "错误" in line or "失败" in line:
            lines.append(line)
        elif NOISE.search(line) and len(lines) < 2:
            lines.append(line)
        if len(lines) >= limit:
            break
    if not lines:
        lines = [line.strip() for line in text.splitlines() if line.strip()][:limit]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract an error signature.")
    parser.add_argument("--file", default="", help="Input log file. Reads stdin when omitted.")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8", errors="replace")
    else:
        text = sys.stdin.read()
    print(extract(text, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
