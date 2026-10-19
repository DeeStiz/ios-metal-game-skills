#!/usr/bin/env python3
"""Validate YAML metadata, skill naming, and local documentation references.

Requires Python 3.14 and PyYAML. This validates structure, not technical correctness.
Run from any directory; --root supports isolated fixture validation.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
try:
    import yaml
except ImportError:
    sys.exit("Install validation dependencies: python3.14 -m pip install -r requirements-dev.txt")

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate fields instead of silently accepting the last value."""


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError(f"duplicate or non-string YAML key: {key!r}")
        result[key] = loader.construct_object(value_node)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def frontmatter(text):
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError("missing YAML frontmatter delimiters")
    fields = yaml.load(parts[1], Loader=UniqueLoader)
    if not isinstance(fields, dict):
        raise ValueError("frontmatter must be a mapping")
    return fields


def validate(root):
    problems = []
    skills_dir = root / "skills"
    skills = sorted(p for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []
    if not skills:
        problems.append("no skill directories found")
    for skill in skills:
        md = skill / "SKILL.md"
        if not md.is_file():
            problems.append(f"{skill.name}: missing SKILL.md")
            continue
        text = md.read_text(encoding="utf-8")
        try:
            fm = frontmatter(text)
            name, desc = fm.get("name"), fm.get("description")
            if not isinstance(name, str) or not NAME.fullmatch(name) or len(name) > 64 or name != skill.name:
                problems.append(f"{skill.name}: invalid or mismatched name {name!r}")
            if not isinstance(desc, str) or not 1 <= len(desc.strip()) <= 1024:
                problems.append(f"{skill.name}: description must contain 1-1024 characters")
        except (ValueError, yaml.YAMLError) as error:
            problems.append(f"{skill.name}: {error}")
        if len(text.splitlines()) > 500:
            problems.append(f"{skill.name}: over 500 lines; move conditional detail to references/")
    docs = [root / "README.md", root / "AGENTS.md", *skills_dir.rglob("*.md")] if skills_dir.exists() else []
    for md in docs:
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8")
        refs = set(re.findall(r"`((?:references|scripts)/[\w./-]+)`", text))
        refs.update(re.findall(r"\]\(([^\s)]+)\)", text))
        for ref in refs:
            parsed = urlsplit(ref.strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (md.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(root.resolve()) or not target.exists():
                problems.append(f"{md.relative_to(root)}: missing or external local reference {ref}")
    return len(skills), problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    count, problems = validate(args.root)
    for problem in problems:
        print("ERROR", problem)
    print(f"{count} skills checked, {len(problems)} problems")
    return int(bool(problems))

if __name__ == "__main__":
    sys.exit(main())
