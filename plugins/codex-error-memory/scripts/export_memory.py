#!/usr/bin/env python3
"""Export Codex error memories to Markdown."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from memory_cli import DEFAULT_DB, connect, get_project, init_db


def main() -> int:
    parser = argparse.ArgumentParser(description="Export error memory as Markdown.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--project", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with connect(Path(args.db)) as conn:
        init_db(conn)
        project_id = get_project(conn, args.project)
        rows = conn.execute(
            """
            SELECT p.*, s.root_cause, s.fix_steps, s.prevention_rule, s.verification_steps,
                   s.files_often_involved, s.commands_often_used
            FROM error_patterns p
            LEFT JOIN solutions s ON s.pattern_id = p.id
            WHERE p.project_id IS NULL OR p.project_id = ?
            ORDER BY p.category, p.title
            """,
            (project_id,),
        ).fetchall()

    parts = ["# Codex Error Memory", ""]
    for row in rows:
        parts.extend(
            [
                f"## {row['title']}",
                "",
                f"- Category: `{row['category']}`",
                f"- Severity: `{row['severity']}`",
                f"- Confidence: `{row['confidence']}`",
                "",
                "### Signature",
                "",
                row["signature"] or "",
                "",
                "### Root Cause",
                "",
                row["root_cause"] or "",
                "",
                "### Fix Steps",
                "",
                row["fix_steps"] or "",
                "",
                "### Prevention",
                "",
                row["prevention_rule"] or "",
                "",
                "### Verification",
                "",
                row["verification_steps"] or "",
                "",
            ]
        )
    Path(args.out).write_text("\n".join(parts), encoding="utf-8")
    print(f"Exported {len(rows)} memories to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
