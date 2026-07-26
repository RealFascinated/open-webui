#!/usr/bin/env python3
"""Apply common TypeScript typing fixes across Svelte files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# (pattern, replacement) — applied to script blocks only
LET_TYPINGS: list[tuple[str, str]] = [
    (r"\blet chat = null\b", "let chat: import('$lib/types/chat').ChatRecord | null = null"),
    (r"\blet note = null\b", "let note: Record<string, unknown> | null = null"),
    (r"\blet files = \[\]\b", "let files: import('$lib/types/chat').ChatFile[] = []"),
    (r"\blet messages = \[\]\b", "let messages: import('$lib/types/chat').ChatMessage[] = []"),
    (r"\blet chatFiles = \[\]\b", "let chatFiles: import('$lib/types/chat').ChatFile[] = []"),
    (r"\blet chatList = null\b", "let chatList: Record<string, unknown>[] | null = null"),
    (r"\blet items = null\b", "let items: Record<string, unknown>[] | null = null"),
    (r"\blet total = null\b", "let total: number | null = null"),
    (r"\blet tags = \[\]\b", "let tags: Record<string, unknown>[] = []"),
    (r"\blet sourceIds = \[\]\b", "let sourceIds: string[] = []"),
    (r"\blet inputFiles\b", "let inputFiles: File[] | undefined"),
    (r"\blet RAGConfig\b", "let RAGConfig: Record<string, unknown>"),
    (r"\blet adminConfig\b", "let adminConfig: Record<string, unknown>"),
    (r"\blet config = \{\}\b", "let config: Record<string, unknown> = {}"),
    (r"\blet generationController = null\b", "let generationController: AbortController | null = null"),
    (r"\blet taskIds = null\b", "let taskIds: string[] | null = null"),
    (r"\blet eventCallback = null\b", "let eventCallback: ((value?: string) => void) | null = null"),
    (r"\blet chatInputElement\b", "let chatInputElement: HTMLTextAreaElement | null"),
    (r"\blet editor = null\b", "let editor: unknown = null"),
    (r"\blet selectedModels = \[''\]", "let selectedModels: string[] = ['']"),
    (r"\blet selectedModelIds = \[\]", "let selectedModelIds: string[] = []"),
    (r"\blet selectedToolIds = \[\]", "let selectedToolIds: string[] = []"),
    (r"\blet selectedSkillIds = \[\]", "let selectedSkillIds: string[] = []"),
    (r"\blet selectedFilterIds = \[\]", "let selectedFilterIds: string[] = []"),
    (r"\blet pendingOAuthTools = \[\]", "let pendingOAuthTools: string[] = []"),
    (r"\blet chatTasks = \[\]", "let chatTasks: unknown[] = []"),
]

HISTORY_INIT = """let history: import('$lib/types/chat').ChatHistory = {
		messages: {},
		currentId: null
	}"""

I18N_PATTERNS = [
    (
        r"import type \{ Writable \} from 'svelte/store';\s*\nimport type \{ i18n as i18nType \} from 'i18next';\s*\n\s*const i18n(?:: Writable<i18nType>)? = getContext\('i18n'\);",
        "import { getI18n } from '$lib/i18n/context';\n\n\tconst i18n = getI18n();",
    ),
    (
        r"const i18n = getContext\('i18n'\);",
        "const i18n = getContext('i18n');",
    ),
]


def extract_scripts(content: str) -> list[tuple[int, int, str, bool]]:
    """Return (start, end, script_body, is_module) for each script block."""
    blocks = []
    for m in re.finditer(r"<script([^>]*)>(.*?)</script>", content, re.DOTALL):
        attrs = m.group(1)
        is_module = "context=\"module\"" in attrs or "context='module'" in attrs
        blocks.append((m.start(2), m.end(2), m.group(2), is_module))
    return blocks


def ensure_lang_ts(content: str) -> tuple[str, bool]:
    changed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal changed
        attrs = m.group(1)
        if "context=\"module\"" in attrs or "context='module'" in attrs:
            return m.group(0)
        if "lang=" in attrs:
            return m.group(0)
        changed = True
        return f"<script lang=\"ts\"{attrs}>{m.group(2)}</script>"

    return re.sub(r"<script([^>]*)>(.*?)</script>", repl, content, flags=re.DOTALL), changed


def fix_script(body: str) -> tuple[str, int]:
    fixes = 0
    original = body

    for pat, repl in LET_TYPINGS:
        body, n = re.subn(pat, repl, body)
        fixes += n

    if re.search(r"let history = \{\s*messages: \{\},\s*currentId: null\s*\}", body):
        body = re.sub(
            r"let history = \{\s*messages: \{\},\s*currentId: null\s*\}",
            HISTORY_INIT,
            body,
            count=1,
        )
        fixes += 1

  # typed event params (conservative)
    for name in ("e", "event", "_e"):
        body, n = re.subn(
            rf"\(({name})\) =>",
            rf"(\1: Event) =>",
            body,
        )
        fixes += n
        body, n = re.subn(
            rf"async \(({name})\) =>",
            rf"async (\1: Event) =>",
            body,
        )
        fixes += n

    for name in ("file", "id"):
        body, n = re.subn(
            rf"\(({name})\) =>",
            rf"(\1: string) =>",
            body,
        )
        fixes += n

    return body, fixes + (1 if body != original else 0)


def process_file(path: Path) -> int:
    content = path.read_text()
    total = 0

    content, lang_changed = ensure_lang_ts(content)
    if lang_changed:
        total += 1

    blocks = extract_scripts(content)
    if not blocks:
        return total

    parts = []
    last = 0
    for start, end, body, is_module in blocks:
        parts.append(content[last:start])
        if is_module:
            parts.append(body)
        else:
            new_body, fixes = fix_script(body)
            parts.append(new_body)
            total += fixes
        last = end
    parts.append(content[last:])
    new_content = "".join(parts)

    if new_content != content:
        path.write_text(new_content)
    return total


def main() -> int:
    total_fixes = 0
    files = sorted(SRC.rglob("*.svelte"))
    for path in files:
        n = process_file(path)
        if n:
            print(f"{path.relative_to(ROOT)}: {n} fixes")
            total_fixes += n
    print(f"Total fixes: {total_fixes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
