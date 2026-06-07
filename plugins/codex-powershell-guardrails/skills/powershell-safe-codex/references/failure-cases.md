# Failure Cases

These are practical failures this plugin is designed to prevent.

## Bash heredoc used in PowerShell

Symptom: `python - <<'PY'` fails or PowerShell treats the body as separate commands.

Fix: use a PowerShell here-string piped to Python:

```powershell
@'
print("ok")
'@ | python -
```

## BOM breaks WeChat Mini Program styles

Symptom: WeChat developer tools report `WXSS 文件编译错误` and `unexpected � at pos 1`.

Cause: a file was saved with UTF-8 BOM, often through PowerShell redirection or old `Set-Content` defaults.

Fix: rewrite the file as UTF-8 without BOM and run the artifact scanner before packaging.

## Environment variables contain hidden BOM

Symptom: login or config lookup silently fails even though `.env` visually looks correct.

Cause: the first key can become `\ufeffKEY`.

Fix: keep `.env` out of release archives, write it explicitly without BOM, and print loaded config keys during diagnostics without printing secrets.

## `rg.exe` is blocked or returns access denied

Symptom: search fails on Windows even though files exist.

Fix: use native PowerShell fallback:

```powershell
Get-ChildItem -Path . -Recurse -Include *.py,*.js,*.json |
  Select-String -Pattern "needle"
```

## Scheduled task finishes but Last Result is 255

Symptom: logs and database show work completed, but Task Scheduler shows a confusing non-zero result.

Cause: wrapper batch file or Python output handling did not normalize exit code and log encoding.

Fix: log start/end, catch exceptions, and end `.bat` with explicit `exit /b 0` after success.

## SSH quoting becomes unstable

Symptom: commands work locally but fail through Paramiko because quotes, `$`, `%`, or backslashes are reinterpreted.

Fix: upload a temporary `.py`, `.ps1`, or `.bat` file, execute it, then delete it. Keep `exec_command` short.

## Remote delete path uses mixed slashes

Symptom: temporary remote file is created but not deleted.

Fix: normalize to the remote shell before deleting:

```python
remote_cmd_path = remote_path.replace("/", "\\")
ssh.exec_command(f'del "{remote_cmd_path}"')
```

## Local API leaks into review or production

Symptom: WeChat app tries to load `http://127.0.0.1:5000/...` and shows `ERR_CONNECTION_REFUSED`.

Cause: cached local asset URL or release config still points to local development.

Fix: scan release folders for `127.0.0.1`, `localhost`, and development ports before upload.

## Release archive includes generated runtime files

Symptom: GitHub tags or upload packages contain `.env`, `.db`, `.log`, `__pycache__`, `.pyc`, import spreadsheets, or temporary backups.

Fix: generate a clean archive and run the artifact scanner in strict mode.

## Flask development server exposed directly on 443

Symptom: public logs contain HTTP/2 probes, `.env` scans, or malformed external requests; service becomes easier to stall.

Fix: use a real edge server such as Nginx or Caddy and keep Python behind a local-only WSGI service.

## Angle brackets in PowerShell arguments

Symptom: PowerShell reports `The '<' operator is reserved for future use` or `RedirectionNotSupported`.

Cause: a placeholder such as `<plugin>` was passed as a raw command argument and PowerShell parsed `<` as syntax.

Fix: avoid angle-bracket placeholders in raw commands. Use neutral placeholders like `[plugin]`, or call a Python script with `subprocess.run([...])` list arguments.

## Chinese path damaged in piped Python

Symptom: a path like `C:\Users\北妖\...` becomes `C:\Users\??\...`, then Python raises `WinError 267` for invalid cwd.

Cause: a Python script piped through PowerShell stdin included a hard-coded non-ASCII path and the console encoding damaged it.

Fix: pass non-ASCII paths through `sys.argv` or environment variables, or run a UTF-8 script file. In the script, print `Path.exists()` before using the path as `cwd`.

## Plugin disappears after cache cleanup

Symptom: a previously working Codex plugin no longer appears after cleaning plugin cache folders.

Cause: installed plugins are loaded from `C:\Users\<user>\.codex\plugins\cache\<marketplace>\<plugin>\<version>`. Removing the whole marketplace cache removes the plugin files.

Fix: only clear targeted staging/cache paths. If already deleted, restore the plugin folder to the cache path, validate it, and ensure `config.toml` still has `[plugins."<plugin>@<marketplace>"] enabled = true`.

## Marketplace update not visible

Symptom: GitHub marketplace has a new plugin but the Codex UI still shows the old plugin list.

Cause: `C:\Users\<user>\.codex\.tmp\marketplaces\<marketplace>` can contain a stale `marketplace.json`.

Fix: compare the remote marketplace file with the local cached one. Refresh the marketplace or clear only that marketplace staging folder, then restart Codex.

## Copy-Item with LiteralPath wildcard does not update files

Symptom: a cache or release folder validates but still contains old file contents after a copy step.

Cause: `-LiteralPath` treats `*` as a literal character. A command like `Copy-Item -LiteralPath 'source\*' ...` does not mean "copy all children".

Fix: use `Copy-Item -Path 'source\*' -Destination target -Recurse -Force` when wildcard expansion is intended, or use `robocopy source target /E` for directory synchronization without deleting extra files.

## Start-Process loses quotes around Program Files path

Symptom: a newly opened PowerShell window reports `The term 'C:\Program' is not recognized`.

Cause: `Start-Process powershell.exe -ArgumentList` launched another parser pass, and the quoted executable path inside the command string lost its quotes. Paths under `C:\Program Files\...` were split at the space.

Fix: use `-EncodedCommand`, a temporary `.ps1` file, or carefully separated arguments. For visible interactive login flows, `-EncodedCommand` is often the least fragile option.
