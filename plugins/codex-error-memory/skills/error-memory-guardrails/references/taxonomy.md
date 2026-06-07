# Error Memory Taxonomy

Use these categories for `error_patterns.category`.

- `shell`: shell syntax, quoting, PowerShell/Bash/cmd differences.
- `encoding`: BOM, mojibake, UTF-8/GBK decoding, hidden config characters.
- `build`: dependency installation, bundling, compiling, packaging.
- `test`: failing tests, missing fixtures, wrong test environment.
- `runtime`: app crashes, API errors, database exceptions, bad state.
- `deploy`: upload, service start, reverse proxy, port, watchdog, scheduled task.
- `config`: `.env`, environment variables, app settings, missing paths.
- `release`: release artifact hygiene, local URL leaks, pycache, logs, databases.
- `git`: branch, tag, remote, archive layout, commit history mistakes.

Severity:

- `low`: nuisance, easy workaround, low blast radius.
- `medium`: blocks local work or risks confusing releases.
- `high`: can break production, corrupt data, leak sensitive data, or block users.

Confidence:

- `1-2`: weak hint.
- `3`: plausible match.
- `4`: strong match.
- `5`: repeated and verified pattern.
