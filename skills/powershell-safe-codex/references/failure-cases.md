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

## PowerShell-written .env breaks WeChat login

Symptom: public `/api/health` still returns 200, but the WeChat Mini Program cannot log in after a backend deployment.

Cause: Windows PowerShell wrote `.env` with UTF-8 BOM. The first key became `\ufeffWX_APPID`, so the backend silently used a default/placeholder AppID while later keys such as MySQL config still appeared normal.

Fix: rewrite `.env` with Python `Path.write_text(..., encoding="utf-8")`, restart the backend, then verify the first bytes are not `EF BB BF`. Confirm `Config.WX_APPID` matches production and `Config.WX_SECRET` is not a placeholder, but never print the secret itself.

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

## Remote PowerShell stdin returns empty output

Symptom: `powershell -NoProfile -ExecutionPolicy Bypass -Command -` through Paramiko exits without useful stdout/stderr, even though the intended script should print diagnostics.

Cause: Windows OpenSSH, PowerShell, and Paramiko stdin handling can be unreliable for multiline scripts.

Fix: write the diagnostic as a temporary UTF-8 `.ps1`, upload it with SFTP, run `powershell -File`, capture stdout/stderr, then delete the remote script.

## Remote JSON with Chinese becomes mojibake

Symptom: a remote Windows Python script prints JSON containing Chinese names, but the local report shows garbled text or must be read as UTF-16 after PowerShell redirection.

Cause: Windows console codepages and PowerShell redirection can transcode text stdout. `print(json.dumps(..., ensure_ascii=False))` is not stable enough across Paramiko, remote cmd, and local redirection.

Fix: on the remote Python side, output explicit UTF-8 bytes:

```python
sys.stdout.buffer.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))
```

Then decode Paramiko stdout as UTF-8 locally. If a local PowerShell redirection already created a UTF-16 file, read it with `encoding="utf-16"`.

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

## New-Item LiteralPath is not available in older Windows PowerShell

Symptom: `New-Item -ItemType Directory -LiteralPath ...` fails with `A parameter cannot be found that matches parameter name 'LiteralPath'`.

Cause: some Windows PowerShell builds do not expose `-LiteralPath` on `New-Item`, even though many other file cmdlets do.

Fix: use `New-Item -ItemType Directory -Path $path` after building the exact path in a variable. For deletes, moves, and reads, continue to prefer cmdlets that support `-LiteralPath`.

## GitHub push is blocked by a dead local proxy

Symptom: `git push` fails with `Failed to connect to github.com port 443 via 127.0.0.1` or `Could not connect to server`.

Cause: global Git config has `http.proxy` or `https.proxy` pointing to a local proxy port, but that proxy process is not running.

Fix: inspect proxy config with `git config --show-origin --get-regexp "http.*proxy|https.*proxy"`. If you do not want to change the global config, run a one-off push with `git -c http.proxy= -c https.proxy= push origin main`.

## Start-Process loses quotes around Program Files path

Symptom: a newly opened PowerShell window reports `The term 'C:\Program' is not recognized`.

Cause: `Start-Process powershell.exe -ArgumentList` launched another parser pass, and the quoted executable path inside the command string lost its quotes. Paths under `C:\Program Files\...` were split at the space.

Fix: use `-EncodedCommand`, a temporary `.ps1` file, or carefully separated arguments. For visible interactive login flows, `-EncodedCommand` is often the least fragile option.

## Local Waitress starts but health check cannot connect

Symptom: `Invoke-WebRequest http://127.0.0.1:5000/api/health` cannot connect after starting `waitress_run.py`.

Causes: the process may have crashed before binding the port. Common causes are missing Python packages such as `pymysql`, or a local `.env` pointing at invalid MySQL credentials.

Fix: inspect redirected `local_waitress_stderr.log` before changing application code. Install missing requirements, or for local-only testing switch the local `.env` to a known local database copy such as SQLite `data.db`.
