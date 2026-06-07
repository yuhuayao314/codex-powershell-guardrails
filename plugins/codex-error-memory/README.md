# Codex Error Memory

A local SQLite-backed memory plugin for recurring technical errors. It helps Codex search previous fixes before debugging and record new lessons after a problem is resolved.

## Install

Install directly:

```powershell
codex plugin install https://github.com/yuhuayao314/codex-error-memory
```

Or install it from the public marketplace repository:

```powershell
codex plugin marketplace add https://github.com/yuhuayao314/codex-plugin-marketplace
```

## Use

Search prior memories:

```powershell
python scripts\memory_cli.py search --project E:\path\to\project --text "error text"
```

Add a memory:

```powershell
python scripts\memory_cli.py add --project E:\path\to\project --title "Short title" --text "error text" --root-cause "Cause" --fix-steps "Fix" --verification-steps "Checks"
```

Export memories:

```powershell
python scripts\export_memory.py --project E:\path\to\project --out memory.md
```

The database is created automatically at `data/error_memory.sqlite`.
