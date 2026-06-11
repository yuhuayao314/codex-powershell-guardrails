# Codex PowerShell Guardrails

A Codex plugin for safer Windows and PowerShell work. It packages one skill and a small scanner that help agents avoid common mistakes when editing Windows projects, automating Windows servers, or preparing release archives.

## What It Helps With

- PowerShell-safe inline Python and command patterns
- UTF-8 BOM checks for WeChat Mini Program files and config files
- Safer Windows file deletion and process inspection
- Paramiko/SSH patterns for Windows Server automation
- Scheduled task logging and explicit exit codes
- Release artifact hygiene before GitHub upload or deployment
- Local and private-network URL leaks such as `127.0.0.1:5000`, `192.168.*`, `10.*`, and `172.16-31.*`
- Common hard-coded secret formats such as OpenAI keys, GitHub tokens, cloud access keys, JWTs, and private-key blocks

## Plugin Contents

- `skills/powershell-safe-codex/SKILL.md`: instructions Codex can load automatically when the task involves Windows or PowerShell.
- `skills/powershell-safe-codex/references/`: practical command patterns and failure cases.
- `scripts/check_windows_artifacts.py`: scanner for release-package mistakes.

## Scanner Usage

From the plugin root:

```powershell
python scripts\check_windows_artifacts.py C:\path\to\project
```

For release archives:

```powershell
python scripts\check_windows_artifacts.py C:\path\to\release --release --strict
```

In `--release` mode the scanner includes `dist/` and `build/` because those directories often contain the actual upload package. For non-release project scans they are skipped by default; add `--include-build` to include them.

Allow local development URLs during local-only checks:

```powershell
python scripts\check_windows_artifacts.py C:\path\to\project --allow-localhost
```

## Installing Locally

This repository is a single plugin root.

Install from a local checkout with Codex:

```powershell
codex plugin install E:\path\to\codex-powershell-guardrails
```

Users can install from the public repository URL:

```powershell
codex plugin install https://github.com/yuhuayao314/codex-powershell-guardrails
```

Or install it from the public marketplace repository:

```powershell
codex plugin marketplace add https://github.com/yuhuayao314/codex-plugin-marketplace
```

## Suggested Use

Ask Codex:

```text
Use PowerShell Guardrails and check this Windows release package before upload.
```

or:

```text
用 PowerShell Guardrails 帮我写一个 Windows Server 上安全执行的 Paramiko 脚本。
```
