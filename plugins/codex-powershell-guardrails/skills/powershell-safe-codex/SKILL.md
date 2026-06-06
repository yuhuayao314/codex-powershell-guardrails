---
name: powershell-safe-codex
description: Always use when Codex will write, review, explain, or run any PowerShell command or script. Also use for Windows terminal work, Windows paths, .ps1/.bat/.cmd files, cmd.exe commands, Windows SSH/Paramiko automation, scheduled tasks, WeChat Mini Program files, release packaging, or any task where Unix shell habits may break on Windows. Helps avoid heredoc mistakes, quoting bugs, UTF-8 BOM issues, unsafe deletes, localhost leaks, pycache/log/env/database artifacts, and unclear task-scheduler exit codes.
---

# PowerShell Safe Codex

Use this skill before writing, reviewing, explaining, or running any PowerShell command. Also use it for Windows terminal work, Windows paths, release packaging, frontend encoding checks, or Windows server automation.

## Default Workflow

1. Identify the shell: PowerShell, `cmd.exe`, Git Bash, remote `cmd`, or remote PowerShell.
2. Prefer short native PowerShell commands. For complex logic, use a PowerShell here-string piped to Python.
3. Avoid Unix-only shell syntax unless the shell is actually Bash.
4. Before editing release artifacts, plan encoding and cleanup checks.
5. After edits, run syntax checks plus the artifact scanner if packaging or uploading.

## Command Patterns

Use these safe defaults:

- Python inline script in PowerShell:

```powershell
@'
print("hello from Python")
'@ | python -
```

- JSON-safe PowerShell output:

```powershell
Get-CimInstance Win32_Process |
  Select-Object ProcessId,CommandLine |
  ConvertTo-Json -Compress
```

- Text search fallback when `rg.exe` fails:

```powershell
Get-ChildItem -Recurse -Include *.py,*.js,*.json |
  Select-String -Pattern "needle"
```

- Safe delete:

```powershell
Remove-Item -LiteralPath $path -Force
```

Never use `python - <<'PY'` in PowerShell. Never enumerate paths in PowerShell and pass them to another shell for deletion.

## Encoding Rules

- Do not use PowerShell redirection or `Set-Content` casually for `.wxss`, `.wxml`, `.js`, `.json`, `.py`, `.toml`, `.yaml`, `.md`.
- Watch for UTF-8 BOM in WeChat Mini Program files; WXSS can fail with `unexpected � at pos 1`.
- Prefer editor-aware patches or scripts that explicitly write `encoding="utf-8"` without BOM.
- After bulk edits, scan for BOM and syntax errors.

## Windows Server / SSH Rules

- For Windows SSH via Paramiko, prefer uploading a short temporary `.py` or `.ps1` script, executing it, then deleting it.
- Decode remote PowerShell/cmd output defensively: try UTF-8 for Python output, GBK for classic Windows command output.
- Avoid deeply nested quoting in `ssh.exec_command`; if command quoting becomes hard to read, use a temporary script.
- For services and scheduled tasks, log explicit start/end status and return explicit exit codes.

## Release Hygiene

Before GitHub upload, deployment, or archive creation, check for:

- `.env`, database files, logs, pycache, `.pyc`
- local-only URLs such as `127.0.0.1`, `localhost`, private server test ports
- generated temp files, backup dumps, spreadsheet imports, screenshots
- BOM in frontend/source files

Run:

```powershell
python scripts/check_windows_artifacts.py <path-to-release>
```

## References

Read only when needed:

- `references/windows-command-patterns.md` for command recipes.
- `references/failure-cases.md` for common Codex-on-Windows failures and fixes.
