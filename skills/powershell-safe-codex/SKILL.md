---
name: powershell-safe-codex
description: Always use when Codex will write, review, explain, or run any PowerShell command or script. Also use for Windows terminal work, Windows paths, .ps1/.bat/.cmd files, cmd.exe commands, Windows SSH/Paramiko automation, scheduled tasks, Codex plugin or marketplace cache work, WeChat Mini Program files, release packaging, or any task where Unix shell habits may break on Windows. Helps avoid heredoc mistakes, quoting bugs, UTF-8/BOM issues, unsafe deletes, localhost leaks, pycache/log/env/database artifacts, invalid plugin cache cleanup, Chinese-path encoding bugs, angle-bracket redirection mistakes, wildcard copy mistakes, Start-Process quoting failures, and unclear task-scheduler exit codes.
---

# PowerShell Safe Codex

Use this skill before writing, reviewing, explaining, or running any PowerShell command. Also use it for Windows terminal work, Windows paths, release packaging, frontend encoding checks, Codex plugin cache/marketplace work, or Windows server automation.

## Default Workflow

1. Identify the shell: PowerShell, `cmd.exe`, Git Bash, remote `cmd`, or remote PowerShell.
2. Prefer short native PowerShell commands. For complex logic, use a PowerShell here-string piped to Python.
3. Avoid Unix-only shell syntax unless the shell is actually Bash.
4. Before editing release artifacts, plan encoding and cleanup checks.
5. Before commands that contain `<`, `>`, `$`, `%`, nested quotes, or Chinese paths, switch to a temporary script, `sys.argv`, or Python `subprocess.run([...])` list arguments.
6. If any command fails, stop and classify the failure before retrying. If `codex-error-memory` is available, search it with the exact error excerpt.
7. After edits, run syntax checks plus the artifact scanner if packaging or uploading.

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

## Argument Safety

- Do not pass placeholder strings like `<plugin>` or `<marketplace>` as raw PowerShell arguments; `<` can be parsed as a redirection operator.
- If arguments contain angle brackets, dollar signs, percent signs, nested quotes, or non-ASCII paths, prefer Python `subprocess.run([...])` from a here-string or a temporary script.
- Avoid hard-coding Chinese Windows paths inside piped stdin scripts. Pass paths through `sys.argv` or environment variables so they are not damaged by console encoding.
- Use `-LiteralPath` for exact paths and `-Path` for wildcard expansion. Do not expect `Copy-Item -LiteralPath '...\*'` to expand `*`.
- When launching a new PowerShell with `Start-Process`, avoid putting a quoted command path inside a single string argument. Use `-EncodedCommand`, a `.ps1` file, or carefully separated `-ArgumentList` items so paths like `C:\Program Files\...` keep their quotes after the second parse.
- When a command fails because of parsing or encoding, do not repeat the same shape. Change transport: native PowerShell cmdlet, here-string, temp script, or list-style subprocess.

## Codex Plugin / Marketplace Rules

- A GitHub repository should be either a single plugin root or a marketplace root. Do not keep both root `.codex-plugin/` and `.agents/plugins/marketplace.json` for long-term publishing.
- For marketplace repos, keep plugins under `plugins/<plugin-name>/` and register them in `.agents/plugins/marketplace.json`.
- Do not delete an entire `C:\Users\<user>\.codex\plugins\cache\<marketplace>` folder casually; installed plugins may be loaded from that cache.
- When debugging plugin visibility, check three places together: marketplace cache, plugin cache, and `C:\Users\<user>\.codex\config.toml` enabled entries.
- If a marketplace update is not visible, compare GitHub `.agents/plugins/marketplace.json` with `C:\Users\<user>\.codex\.tmp\marketplaces\<marketplace>\.agents\plugins\marketplace.json`.

## Encoding Rules

- Do not use PowerShell redirection or `Set-Content` casually for `.wxss`, `.wxml`, `.js`, `.json`, `.py`, `.toml`, `.yaml`, `.md`.
- Watch for UTF-8 BOM in WeChat Mini Program files; WXSS can fail with `unexpected � at pos 1`.
- Treat `.env` as especially sensitive to BOM. In Windows PowerShell, `Set-Content -Encoding UTF8` can write a BOM; if `.env` starts with BOM, the first key can become `\ufeffWX_APPID` and production WeChat login can fail.
- Prefer editor-aware patches or scripts that explicitly write `encoding="utf-8"` without BOM.
- After editing `.env` or release config, verify the first bytes are not `EF BB BF` and verify critical keys load by name without printing secret values.
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
