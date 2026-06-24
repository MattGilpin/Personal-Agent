---
created: 2026-06-24T17:30:00+04:00
updated: 2026-06-24T17:30:00+04:00
type: system
---

# Vault Editing Protocol

Use this before every edit to Matt's vault at `~/.hermes/vault`.

Matt's rule: vault notes must always be timestamped, chronological, supersession-aware, and free of em/en dashes.

## Trigger Conditions

Load this skill when:
- Writing or updating any file under `~/.hermes/vault/`
- Saving a date, appointment, contact detail, or project update
- Updating work, personal, or reference material

## Required Workflow

1. **Resolve the path.** Know exactly which file you are editing.

2. **Read before writing.** Always read the target file first.

3. **Timestamp every edit.**
   - Frontmatter `updated: YYYY-MM-DDTHH:MM+04:00`
   - New files include both `created:` and `updated:`

4. **Preserve history.**
   - Never delete old facts.
   - Mark old entries as `Superseded [date]`.

5. **Chronological order.**
   - Dated entries, tables, and timelines: oldest to newest.
   - Insert new entries in position, not just at the bottom.

6. **Supersession-aware.**
   - When a fact changes, keep the old entry marked Superseded and add the new one with the current date.

7. **No em dashes or en dashes.**
   - Use commas, periods, or hyphens instead.

8. **Validate after editing.**
   - Run: `python3 ~/.hermes/vault/_System/scripts/vault-lint.py check [file] --full`
   - Fix any errors in your newly added lines.

9. **Commit durable changes.**
   - The vault is a git repo at `~/.hermes/vault`.
   - Stage the exact edited files.
   - Run the staged validator: `python3 ~/.hermes/vault/_System/scripts/vault-lint.py staged`
   - Commit with a message saying what changed and why.

## Folder Structure

- Personal/: identity, health, finance, household, admin
- Work/: business projects, clients, meetings
- Projects/: active and archived projects
- Contacts/: people network
- Reference-Data/: research, transcripts, dated reference material
- _System/: vault governance, scripts, protocols

## Vault-Lint

- Validator: `~/.hermes/vault/_System/scripts/vault-lint.py`
- Pre-commit hook: `~/.hermes/vault/.git/hooks/pre-commit`

The hook blocks staged markdown commits that violate:
- Missing timestamp on edited markdown
- Out-of-order chronological tables
- Newly added em dashes or en dashes
