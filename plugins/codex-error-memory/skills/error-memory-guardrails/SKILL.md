---
name: error-memory-guardrails
description: Always use when Codex sees an error message, stack trace, failed command, failing test, build error, compile error, runtime exception, deployment failure, recurring bug, or the user says 又报错了, 还是不行, 上次那个问题, 网络异常, 编译失败, 登录不上, 运行失败, or similar. Search the local error-memory database before proposing fixes; after a new technical issue is resolved, record the reusable lesson. Do not store reality-policy or platform-review decisions as default memories.
---

# Error Memory Guardrails

Use this skill before diagnosing technical failures. The goal is to make Codex learn from repeated project errors without pretending the model itself has permanent memory.

## Default Workflow

1. Capture a short error excerpt: command output, stack trace, build message, runtime symptom, or user-described failure.
2. Run a memory search before proposing a fix:

```powershell
python plugins\codex-error-memory\scripts\memory_cli.py search --project <project-root> --text "<error excerpt>"
```

3. If a high-confidence result appears, explain why it may match, then verify against the current project before editing.
4. If there is no useful match, debug systematically with normal project evidence.
5. After the issue is resolved, add a reusable technical memory. Treat this as the default after any new technical failure that required investigation, unless the user says not to write memory:

```powershell
python plugins\codex-error-memory\scripts\memory_cli.py add --project <project-root> --title "<short title>" --error-file error.txt --root-cause "<cause>" --fix-steps "<steps>" --verification-steps "<checks>"
```

6. Record an occurrence when a known issue appears again.
7. If another plugin, such as `codex-powershell-guardrails`, is active and the failure belongs to that plugin's domain, apply that plugin's rules immediately after the memory search. The memory plugin remembers; the domain plugin prevents repeat mistakes.

## What To Store

Store technical, repeatable engineering lessons:

- shell syntax mistakes
- encoding and BOM failures
- dependency, build, compile, and test failures
- runtime exceptions
- deployment and service-start issues
- release-package leaks such as local URLs, generated files, logs, or databases
- git, tag, branch, and archive-structure mistakes

## What Not To Store

Do not store:

- secrets, full tokens, passwords, private keys, full `.env` contents
- long raw logs when a short excerpt is enough
- platform-review or reality-policy choices that may change with product strategy
- user personal information

## Privacy Rule

Before adding a memory, sanitize the excerpt. The CLI masks common secrets, tokens, openids, emails, phone-like values, and long bearer strings.

## References

Read only when needed:

- `references/taxonomy.md` for categories and severity.
- `references/review-template.md` for a good post-fix memory format.
