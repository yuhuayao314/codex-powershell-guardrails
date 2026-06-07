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

For non-ASCII paths, pass the path as an argument instead of hard-coding it in the piped script:

```powershell
$target = 'C:\Users\北妖\project'
@'
import sys
from pathlib import Path
target = Path(sys.argv[1])
print(target, target.exists())
'@ | python - $target
```

For arguments containing characters PowerShell may parse, use Python list arguments:

```powershell
@'
import subprocess
subprocess.run([
    "python",
    "scripts\\memory_cli.py",
    "search",
    "--text",
    "literal text with [plugin] placeholder"
], check=True)
'@ | python -
```

Use `-Path` for wildcard expansion and `-LiteralPath` only for exact paths:

```powershell
Copy-Item -Path 'C:\source\*' -Destination 'C:\target' -Recurse -Force
```

For directory synchronization that should keep extra target files such as a local SQLite database, prefer `robocopy` without `/MIR`:

```powershell
robocopy 'C:\source' 'C:\target' /E /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -le 7) { exit 0 } else { exit $LASTEXITCODE }
```

When opening a visible PowerShell window with a command path that contains spaces, encode the command instead of relying on nested quotes:

```powershell
$cmd = "& 'C:\Program Files\GitHub CLI\gh.exe' auth status"
$encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($cmd))
Start-Process powershell.exe -ArgumentList @('-NoExit', '-EncodedCommand', $encoded)
```

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
