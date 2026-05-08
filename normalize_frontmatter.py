#!/usr/bin/env python3
"""normalize_frontmatter.py <src.md> <dest.md>

Reads an Obsidian Markdown file, normalises its frontmatter to be
Astro content-collection compatible, and writes the result to dest.

Transformations applied
  - Maps `date` → `pubDate`  (Obsidian default → Astro schema field)
  - Adds `pubDate` (today's date) if absent
  - Adds `title` (derived from filename) if absent; always double-quotes it
  - Adds `description: ""` if absent; always double-quotes it
  - Adds `tags: []` if absent
  - Converts YAML block-style tag lists to inline YAML array
  - Drops Obsidian-only keys: aliases, alias, cssclass, cssClasses, publish
  - Outputs keys in canonical Astro order
"""

import re
import sys
from datetime import date
from pathlib import Path

FRONTMATTER_RE = re.compile(r'\A---[ \t]*\n(.*?)\n---[ \t]*\n?', re.DOTALL)
OBSIDIAN_DROP = {'aliases', 'alias', 'cssclass', 'cssClasses', 'publish'}
KEY_ORDER = ['title', 'description', 'pubDate', 'updatedDate', 'tags']


def _dquote(val: str) -> str:
    """Return val as a safely double-quoted YAML string scalar."""
    s = val.strip()
    # Strip existing outer quotes
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        s = s[1:-1]
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Return (fm_dict, body). All fm values are raw strings."""
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw

    fm: dict[str, str] = {}
    body = raw[m.end():]
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or ':' not in line:
            i += 1
            continue
        key, _, val = line.partition(':')
        key, val = key.strip(), val.strip()
        # Block sequence: `key:` followed by indented `- item` lines
        if not val and i + 1 < len(lines) and re.match(r'^\s+-', lines[i + 1]):
            items = []
            i += 1
            while i < len(lines) and re.match(r'^\s+-', lines[i]):
                item = re.sub(r'^\s+-\s*', '', lines[i]).strip()
                items.append(f'"{item}"')
                i += 1
            fm[key] = '[' + ', '.join(items) + ']'
            continue
        fm[key] = val
        i += 1

    return fm, body


def build_frontmatter(fm: dict) -> str:
    lines = ['---']
    written: set[str] = set()

    def emit(k: str) -> None:
        if k in fm:
            lines.append(f'{k}: {fm[k]}')
            written.add(k)

    for key in KEY_ORDER:
        emit(key)
    for key in fm:
        if key not in written:
            lines.append(f'{key}: {fm[key]}')

    lines.append('---')
    return '\n'.join(lines)


def normalize(src: Path, dest: Path) -> None:
    content = src.read_text(encoding='utf-8')
    fm, body = parse_frontmatter(content)

    # Drop Obsidian-only keys
    for k in OBSIDIAN_DROP:
        fm.pop(k, None)

    # date → pubDate
    if 'date' in fm and 'pubDate' not in fm:
        fm['pubDate'] = fm.pop('date')

    # Required Astro fields with safe defaults
    fm.setdefault('pubDate', date.today().isoformat())

    if 'title' not in fm:
        fm['title'] = _dquote(src.stem.replace('-', ' ').replace('_', ' ').title())
    else:
        fm['title'] = _dquote(fm['title'])

    if 'description' not in fm:
        fm['description'] = '""'
    else:
        fm['description'] = _dquote(fm['description'])

    fm.setdefault('tags', '[]')

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(build_frontmatter(fm) + '\n' + body, encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <src.md> <dest.md>', file=sys.stderr)
        sys.exit(1)
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    normalize(src, dest)
    print(f'[normalize] {src.name} → {dest}')
