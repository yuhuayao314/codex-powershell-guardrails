# Windows Command Patterns

## Inline Python

PowerShell does not support Bash heredocs.

Bad:

```powershell
python - <<'PY'
print("x")
PY
```

Good:

```powershell
@'
print("x")
'@ | python -
```

For scripts with paths or quotes, this is safer than a one-line `python -c`.

## Search

Prefer `rg` when it works, but Windows installs sometimes fail with `Access is denied`.

Fallback:

```powershell
Get-ChildItem -Path . -Recurse -Include *.py,*.js,*.json,*.wxml,*.wxss |
  Select-String -Pattern "needle"
```

For file names:

```powershell
Get-ChildItem -Path . -Recurse -Filter *.py
```

## Read Files

Use `Get-Content` for short files:

```powershell
Get-Content -Path .\server\app.py -TotalCount 120
```

Use `Select-Object -Skip` for a slice:

```powershell
Get-Content .\server\app.py | Select-Object -Skip 500 -First 80
```

## Safe File Deletion

Use one shell end to end.

```powershell
$target = Resolve-Path .\release\__pycache__
Remove-Item -LiteralPath $target -Recurse -Force
```

Do not pipe PowerShell-discovered paths into `cmd /c del` or another shell.

## Process Inspection

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq 'python.exe' } |
  Select-Object ProcessId,CommandLine |
  ConvertTo-Json -Compress
```

## Port Checks

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 5000
netstat -ano | findstr :443
```

## Scheduled Task Batch Exit Codes

End `.bat` files explicitly:

```bat
python -u C:\path\script.py >> C:\path\task.log 2>&1
if errorlevel 1 (
  echo [%date% %time%] failed with code %errorlevel% >> C:\path\task.log
  exit /b 1
)
echo [%date% %time%] finished >> C:\path\task.log
exit /b 0
```

## Paramiko to Windows

Prefer temporary scripts:

```python
remote = "C:/aiqiandao/server/_codex_tmp.py"
sftp.file(remote, "w").write(script)
ssh.exec_command(f'cd /d C:\\aiqiandao\\server && python "{remote}"')
ssh.exec_command('del "' + remote.replace("/", "\\") + '"')
```

Decode output defensively:

```python
stdout.read().decode("utf-8", errors="replace")
stderr.read().decode("gbk", errors="replace")
```
