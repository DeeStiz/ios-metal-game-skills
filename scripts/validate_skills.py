#!/usr/bin/env python3
"""Check every skills/<name>/SKILL.md against the Agent Skills format.

- frontmatter between --- lines with `name` and `description`
- name: 1-64 chars, lowercase letters, digits and single hyphens, equal to the folder name
- description: 1-1024 chars
- files referenced as references/... or scripts/... exist
Exit status 1 on any problem. No third-party dependencies.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')
    return fields


def main() -> int:
    problems = []
    skills = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    for skill in skills:
        md = skill / "SKILL.md"
        if not md.exists():
            problems.append(f"{skill.name}: missing SKILL.md")
            continue
        text = md.read_text()
        fm = frontmatter(text)
        if fm is None:
            problems.append(f"{skill.name}: no YAML frontmatter")
            continue
        name, desc = fm.get("name", ""), fm.get("description", "")
        if not NAME.match(name) or len(name) > 64:
            problems.append(f"{skill.name}: invalid name {name!r}")
        if name != skill.name:
            problems.append(f"{skill.name}: name {name!r} does not match folder")
        if not 1 <= len(desc) <= 1024:
            problems.append(f"{skill.name}: description length {len(desc)} (1-1024)")
        if len(text.splitlines()) > 500:
            problems.append(f"{skill.name}: SKILL.md over 500 lines; move detail to references/")
        for ref in set(re.findall(r"`((?:references|scripts)/[\w./-]+)`", text)):
            if not (skill / ref).exists():
                problems.append(f"{skill.name}: referenced file {ref} not found")
    for p in problems:
        print("ERROR", p)
    print(f"{len(skills)} skills checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
