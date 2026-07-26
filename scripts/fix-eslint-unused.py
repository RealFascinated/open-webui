#!/usr/bin/env python3
"""Safely fix @typescript-eslint/no-unused-vars using usage analysis."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULE = '@typescript-eslint/no-unused-vars'


def run_eslint() -> list[dict]:
    out = Path('/tmp/eslint-unused.json')
    subprocess.run(
        ['npx', 'eslint', 'src', '--format', 'json', '-o', str(out)],
        cwd=ROOT,
        capture_output=True,
    )
    return json.loads(out.read_text() or '[]')


def template_part(text: str) -> str:
    idx = text.find('</script>')
    return text[idx:] if idx != -1 else ''


def symbol_used(text: str, symbol: str, skip_line: int | None = None) -> bool:
    template = template_part(text)
    if re.search(rf'\${re.escape(symbol)}\b', template):
        return True
    if re.search(rf'(?<![\w$]){re.escape(symbol)}(?![\w$])', template):
        return True

    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        if skip_line == i:
            continue
        if re.search(rf'\${re.escape(symbol)}\b', line):
            return True
        if re.search(rf'(?<![\w$]){re.escape(symbol)}(?![\w$])', line):
            return True
    return False


def remove_import_symbol(text: str, symbol: str) -> tuple[str, bool]:
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        prefix, inner, suffix = match.group(1), match.group(2), match.group(3)
        parts = []
        for part in inner.split(','):
            p = part.strip()
            if not p:
                continue
            alias = re.split(r'\s+as\s+', p)[-1].strip()
            if alias == symbol:
                changed = True
            else:
                parts.append(p)
        if not parts:
            return ''
        return f'{prefix}{", ".join(parts)}{suffix}'

    text = re.sub(
        r'(import\s+(?:type\s+)?[^;\n]*\{)([^}]+)(\}\s*from\s*[^;\n]+;)',
        repl,
        text,
    )
    default = rf'^\s*import\s+{re.escape(symbol)}\s+from\s+[^;\n]+;\s*\n?'
    if re.search(default, text, re.M):
        text = re.sub(default, '', text, count=1, flags=re.M)
        changed = True
    if changed:
        text = re.sub(r'\n{3,}', '\n\n', text)
    return text, changed


def prefix_on_line(line: str, symbol: str) -> str:
    return re.sub(rf'\b{re.escape(symbol)}\b', f'_{symbol}', line, count=1)


def safe_delete_line(lines: list[str], idx: int) -> bool:
    line = lines[idx]
    next_line = lines[idx + 1] if idx + 1 < len(lines) else ''
    if re.search(r'=\s*\{\s*$', line.rstrip()):
        return False
    if re.match(r'^\s*\w+\s*:', next_line):
        return False
    del lines[idx]
    return True


def fix_message(path: Path, symbol: str, line_no: int, message: str) -> bool:
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return False

    line = lines[idx]

    if 'is defined but never used' in message and not symbol_used(text, symbol, skip_line=line_no):
        new_text, changed = remove_import_symbol(text, symbol)
        if changed:
            path.write_text(new_text)
            return True

    if 'args must match' in message or (
        'is defined but never used' in message
        and re.search(rf'\(\s*[^)]*\b{re.escape(symbol)}\b', line)
    ):
        if re.search(rf'\b{re.escape(symbol)}\b', line):
            lines[idx] = prefix_on_line(line, symbol)
            path.write_text(''.join(lines))
            return True

    if symbol == 'dispatch' and 'dispatch' in line and 'createEventDispatcher' in text:
        if not symbol_used(text, 'dispatch', skip_line=line_no):
            new_text = re.sub(r'^\s*const dispatch = createEventDispatcher[^;]*;\s*\n', '', text, flags=re.M)
            new_text, _ = remove_import_symbol(new_text, 'createEventDispatcher')
            if new_text != text:
                path.write_text(new_text)
                return True

    if symbol == 'createEventDispatcher':
        new_text, changed = remove_import_symbol(text, symbol)
        if changed:
            path.write_text(new_text)
            return True

    if not symbol_used(text, symbol, skip_line=line_no):
        if re.search(rf'^\s*(?:export\s+)?(?:const|let)\s+{re.escape(symbol)}\b', line):
            if safe_delete_line(lines, idx):
                path.write_text(''.join(lines))
                return True
        if re.search(rf'^\s*\$:\s*{re.escape(symbol)}\s*=', line):
            if safe_delete_line(lines, idx):
                path.write_text(''.join(lines))
                return True

    if 'assigned a value but never used' in message and not symbol_used(text, symbol, skip_line=line_no):
        if re.search(rf'^\s*(?:export\s+)?(?:const|let)\s+{re.escape(symbol)}\b', line):
            if safe_delete_line(lines, idx):
                path.write_text(''.join(lines))
                return True
        if re.search(rf'\b{re.escape(symbol)}\s*=', line) and 'let ' not in line and 'const ' not in line:
            # assignment to unused binding in destructuring or param
            if re.search(rf'\b{re.escape(symbol)}\b', line):
                lines[idx] = prefix_on_line(line, symbol)
                path.write_text(''.join(lines))
                return True

    return False


def main() -> int:
    for round_no in range(1, 8):
        data = run_eslint()
        fixes = 0
        for file_result in data:
            path = Path(file_result['filePath'])
            msgs = [m for m in file_result.get('messages', []) if m.get('ruleId') == RULE]
            for msg in sorted(msgs, key=lambda m: m['line'], reverse=True):
                m = re.search(r"'([^']+)'", msg['message'])
                if not m:
                    continue
                if fix_message(path, m.group(1), msg['line'], msg['message']):
                    fixes += 1
        remaining = sum(
            1 for fr in data for m in fr.get('messages', []) if m.get('ruleId') == RULE
        )
        print(f'round {round_no}: fixes={fixes} remaining={remaining}')
        if fixes == 0:
            break

    proc = subprocess.run(['npm', 'run', 'lint:frontend'], cwd=ROOT)
    return proc.returncode


if __name__ == '__main__':
    raise SystemExit(main())
