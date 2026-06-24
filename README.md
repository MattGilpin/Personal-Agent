---
created: 2026-06-24T17:30:00+04:00
updated: 2026-06-24T17:30:00+04:00
type: system
---

# Matt Taylor - Personal Knowledge Vault

This vault stores Matt's personal knowledge, managed by his Hermes PA agent.

## Folder Structure

- Personal/: identity, health, finance, household, admin
- Work/: business projects, clients, meetings
- Projects/: active and archived projects
- Contacts/: people network
- Reference-Data/: research, transcripts, dated reference material
- _System/: vault governance, scripts, protocols

## Governance

All vault edits follow the [Vault Editing Protocol](_System/Vault-Editing-Protocol.md):
- Every edit is timestamped
- Chronological order maintained
- Supersession-aware (old facts preserved, marked superseded)
- No em dashes or en dashes
- Validated by vault-lint.py before commit

## Git

The vault is a git repo. Binary attachments are gitignored.
Commits require passing the pre-commit hook (vault-lint staged validation).
