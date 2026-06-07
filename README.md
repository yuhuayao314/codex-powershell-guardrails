# yuhuayao314 Codex Plugins

This repository is a small Codex plugin marketplace.

## Plugins

### PowerShell Guardrails

`codex-powershell-guardrails` helps Codex work more safely on Windows and PowerShell:

- PowerShell-safe inline Python and command patterns
- UTF-8 BOM checks
- safer Windows file deletion and process inspection
- Windows SSH / Paramiko patterns
- scheduled task exit-code guidance
- release artifact hygiene checks

### Codex Error Memory

`codex-error-memory` helps Codex remember recurring technical errors:

- searches a local SQLite memory before debugging
- stores technical error signatures, root causes, fixes, prevention rules, and verification steps
- keeps memories project-scoped when a project path is supplied
- includes built-in technical memories for shell, encoding, release, deploy, config, and git mistakes
- avoids storing secrets, long raw logs, user personal information, and reality-policy decisions

## Marketplace Layout

```text
.agents/plugins/marketplace.json
plugins/
  codex-powershell-guardrails/
  codex-error-memory/
```

Add this repository as a marketplace in Codex, then install the plugin you want from `yuhuayao314 Plugins`.

## Direct Local Use

PowerShell Guardrails scanner:

```powershell
python plugins\codex-powershell-guardrails\scripts\check_windows_artifacts.py C:\path\to\release --release --strict
```

Error Memory search:

```powershell
python plugins\codex-error-memory\scripts\memory_cli.py search --project C:\path\to\project --text "error text"
```
