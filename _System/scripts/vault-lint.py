#!/usr/bin/env python3
"""
vault-lint.py - enforce Lotty Ashburn's vault editing protocol.

Rules:
1. Staged markdown must be timestamped (frontmatter updated: or dated line).
2. Chronological tables must be oldest to newest.
3. No em dashes or en dashes in new edits.
4. Notes should carry type in frontmatter.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

VAULT = Path.home() / '.hermes' / 'vault'
EM_DASH = '\u2014'
EN_DASH = '\u2013'

CHRONO_HEADINGS = re.compile(
    r'timeline|chronolog|appointment|upcoming|birthday|deadline|schedule|log\b',
    re.IGNORECASE,
)
DATE_TOKEN = re.compile(r'\d{4}-\d{2}-\d{2}')
HEADING_RE = re.compile(r'^#{1,6}\s+(.+?)\s*$', re.MULTILINE)


def dubai_now() -> datetime:
    if ZoneInfo:
        return datetime.now(ZoneInfo('Asia/Dubai'))
    return datetime.utcnow()


def today_dubai() -> str:
    return dubai_now().date().isoformat()


def iso_dubai_minutes() -> str:
    return dubai_now().isoformat(timespec='minutes')


def parse_date(text: str):
    m = re.search(r'\d{4}-\d{2}-\d{2}', text or '')
    if m:
        try:
            return datetime.strptime(m.group(0), '%Y-%m-%d').date()
        except ValueError:
            pass
    months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
              'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
    m = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', text or '', re.IGNORECASE)
    if m:
        day = int(m.group(1))
        mon = months[m.group(2).lower()]
        return datetime(2026, mon, day).date()
    return None


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == '':
        return ''
    if value.startswith('[') and value.endswith(']'):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip('"\'') for part in inner.split(',') if part.strip()]
    return value.strip('"\'')


def value_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, list):
        return ', '.join(str(v) for v in value)
    return str(value)


def frontmatter(lines: list[str]) -> dict[str, Any]:
    if not lines or lines[0].strip() != '---':
        return {}
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            end = i
            break
    if end is None:
        return {}
    out: dict[str, Any] = {}
    current_key: str | None = None
    for line in lines[1:end]:
        m = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
        if m:
            current_key = m.group(1).strip()
            out[current_key] = parse_scalar(m.group(2))
            continue
        item = re.match(r'^\s+-\s+(.*)$', line)
        if item and current_key:
            existing = out.get(current_key)
            if not isinstance(existing, list):
                existing = [] if existing in ('', None) else [existing]
            existing.append(item.group(1).strip().strip('"\''))
            out[current_key] = existing
    return out


def rel_path(path: Path) -> str:
    try:
        return path.relative_to(VAULT).as_posix()
    except ValueError:
        return path.as_posix()


def added_lines_for_staged(rel: str) -> list[str]:
    try:
        d = subprocess.run(
            ['git', '-C', str(VAULT), 'diff', '--cached', '--unified=0', '--', rel],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        return []
    added = []
    for line in d.stdout.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            added.append(line[1:])
    return added


def validate_file(path: Path, full_dash: bool = False, added_lines: list[str] | None = None,
                  staged: bool = False) -> list[tuple[str, int, str]]:
    issues: list[tuple[str, int, str]] = []
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return [('ERROR', 0, f'unreadable: {e}')]
    lines = text.splitlines()
    fm = frontmatter(lines)

    # Dash enforcement
    if full_dash:
        for idx, line in enumerate(lines, 1):
            if EM_DASH in line:
                issues.append(('ERROR', idx, 'em dash present, replace with comma/period'))
            if EN_DASH in line:
                issues.append(('ERROR', idx, 'en dash present, replace with hyphen/comma/period'))
    elif added_lines is not None:
        for line in added_lines:
            if EM_DASH in line:
                issues.append(('ERROR', 0, 'em dash in added line, replace with comma/period'))
            if EN_DASH in line:
                issues.append(('ERROR', 0, 'en dash in added line, replace with hyphen/comma/period'))

    # Frontmatter date sanity
    created = parse_date(value_text(fm.get('created')) or value_text(fm.get('start_date')))
    updated = parse_date(value_text(fm.get('updated')))
    if created and updated and updated < created:
        issues.append(('ERROR', 0, f'frontmatter updated ({updated}) before created ({created})'))

    # Timestamp enforcement for staged edits
    if staged:
        added_blob = '\n'.join(added_lines or [])
        has_updated = bool(value_text(fm.get('updated')).strip())
        today_added = today_dubai() in added_blob
        if not has_updated and not today_added:
            issues.append(('ERROR', 0,
                           f'edited markdown must be timestamped: add frontmatter updated: {iso_dubai_minutes()} '
                           f'or a dated line containing {today_dubai()}'))

    # Chronological table checks
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith('#') and CHRONO_HEADINGS.search(line):
            heading = re.sub(r'^#+\s*', '', line.strip())
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('|'):
                if lines[j].lstrip().startswith('#'):
                    break
                j += 1
            dates: list[tuple[int, object, str]] = []
            while j < len(lines) and lines[j].strip().startswith('|'):
                row = lines[j].strip()
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if cells and not set(cells[0]) <= set('-: '):
                    d = parse_date(cells[0])
                    if d:
                        dates.append((j + 1, d, cells[0]))
                j += 1
            for k in range(1, len(dates)):
                if dates[k][1] < dates[k - 1][1]:
                    issues.append(('ERROR', dates[k][0],
                                   f"chronological order broken in '{heading}': '{dates[k][2]}' before '{dates[k-1][2]}'"))
            i = j
            continue
        i += 1

    return issues


def print_issues(label: str, issues: list[tuple[str, int, str]]) -> bool:
    has_error = False
    for sev, line, msg in issues:
        loc = f'{label}:{line}' if line else label
        print(f'{sev} {loc}  {msg}')
        has_error = has_error or sev == 'ERROR'
    return has_error


def cmd_check(args) -> int:
    path = Path(args.file)
    if not path.exists():
        print(f'ERROR: file not found: {path}', file=sys.stderr)
        return 2
    issues = validate_file(path, full_dash=args.full)
    return 1 if print_issues(str(path), issues) else 0


def cmd_staged(args) -> int:
    try:
        out = subprocess.run(
            ['git', '-C', str(VAULT), 'diff', '--cached', '--name-only', '--diff-filter=AM'],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f'ERROR: git diff failed: {e}', file=sys.stderr)
        return 2
    files = [f for f in out.stdout.splitlines() if f.endswith('.md')]
    has_error = False
    for rel in files:
        path = VAULT / rel
        if not path.exists():
            continue
        issues = validate_file(path, added_lines=added_lines_for_staged(rel), staged=True)
        has_error = print_issues(rel, issues) or has_error
    return 1 if has_error else 0


def cmd_fix_dates(args) -> int:
    path = Path(args.file)
    if not path.exists():
        print(f'ERROR: file not found: {path}', file=sys.stderr)
        return 2
    text = path.read_text(encoding='utf-8')
    stamp = iso_dubai_minutes()
    if text.startswith('---'):
        lines = text.splitlines(keepends=True)
        end = None
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                end = i
                break
        if end is not None:
            block = lines[1:end]
            replaced = False
            for idx, line in enumerate(block):
                if re.match(r'^updated:\s*', line):
                    block[idx] = f'updated: {stamp}\n'
                    replaced = True
                    break
            if not replaced:
                insert_at = 0
                for idx, line in enumerate(block):
                    if re.match(r'^(title|name|created|start_date):\s*', line):
                        insert_at = idx + 1
                block.insert(insert_at, f'updated: {stamp}\n')
            path.write_text(''.join(lines[:1] + block + lines[end:]), encoding='utf-8')
            print(f'updated: {path} -> updated: {stamp}')
            return 0
    path.write_text(text.rstrip() + f'\n\n## Update {stamp}\n\n', encoding='utf-8')
    print(f'appended dated update marker: {path} -> {stamp}')
    return 0


def cmd_scan(args) -> int:
    root = Path(args.path) if args.path else VAULT
    count = 0
    err_files = 0
    for path in sorted(root.rglob('*.md')):
        if '.git' in path.parts:
            continue
        count += 1
        issues = validate_file(path, full_dash=True)
        errs = [i for i in issues if i[0] == 'ERROR']
        if errs:
            err_files += 1
            rel = rel_path(path)
            for issue in errs[:3]:
                print_issues(rel, [issue])
    print(f'\n{err_files}/{count} files have ERRORs in full scan.')
    print('Pre-existing errors are baseline; staged hook blocks new drift only.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Lotty vault editing protocol validator')
    sub = parser.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check')
    c.add_argument('file')
    c.add_argument('--full', action='store_true')
    c.set_defaults(func=cmd_check)
    s = sub.add_parser('staged')
    s.set_defaults(func=cmd_staged)
    f = sub.add_parser('fix-dates')
    f.add_argument('file')
    f.set_defaults(func=cmd_fix_dates)
    sc = sub.add_parser('scan')
    sc.add_argument('--path')
    sc.set_defaults(func=cmd_scan)
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
