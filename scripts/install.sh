#!/bin/bash
# Install skill folders for supported agents. Existing skills are preserved by default.
# Usage: scripts/install.sh [--agent NAME]... [--project DIR] [--link]
#                          [--skill NAME]... [--replace]
# Agents: claude, codex, copilot, gemini, agents, all (default: all).
# --replace moves existing folders/symlinks to a unique sibling backup directory.
# --project must exist. --link uses absolute symlinks that follow repository updates.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
agents=() skills=() destinations=() project="" link=0 replace=0
fail() { echo "$*" >&2; exit 2; }
value() { [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || fail "missing value for $1"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) value "$@"; agents+=("$2"); shift 2 ;;
    --project) value "$@"; project="$(cd "$2" && pwd)"; shift 2 ;;
    --skill) value "$@"; skills+=("$2"); shift 2 ;;
    --link) link=1; shift ;;
    --replace) replace=1; shift ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
done
[[ ${#agents[@]} -gt 0 ]] || agents=(all)
# Validate the complete request before creating directories or replacing anything.
for agent in "${agents[@]}"; do
  case "$agent" in claude|codex|copilot|gemini|agents|all) ;; *) fail "unknown agent: $agent" ;; esac
done
[[ " ${agents[*]} " != *" all "* ]] || agents=(claude codex copilot gemini)
if [[ ${#skills[@]} -eq 0 ]]; then
  for d in "$repo"/skills/*/; do skills+=("$(basename "$d")"); done
fi
for s in "${skills[@]}"; do
  [[ "$s" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || fail "invalid skill name: $s"
  [[ -f "$repo/skills/$s/SKILL.md" ]] || fail "no such skill: $s"
done
for agent in "${agents[@]}"; do
  case "$agent" in
    claude) folder=.claude/skills ;;
    codex|agents) folder=.agents/skills ;;
    copilot) if [[ -n "$project" ]]; then folder=.github/skills; else folder=.copilot/skills; fi ;;
    gemini) folder=.gemini/skills ;;
  esac
  dest="${project:-$HOME}/$folder"
  duplicate=0
  for existing in "${destinations[@]+"${destinations[@]}"}"; do
    [[ "$existing" != "$dest" ]] || duplicate=1
  done
  [[ $duplicate -eq 1 ]] || destinations+=("$dest")
done
stage=""
trap '[[ -z "$stage" ]] || rm -rf "$stage"' EXIT
for dest in "${destinations[@]}"; do
  mkdir -p "$dest"
  for s in "${skills[@]}"; do
    target="$dest/$s"
    if [[ -e "$target" || -L "$target" ]]; then
      if [[ $replace -eq 0 ]]; then echo "preserved existing: $target (use --replace to back up and replace)"; continue; fi
    fi
    stage=$(mktemp -d "$(dirname "$dest")/.skill-stage.XXXXXX")
    if [[ $link -eq 1 ]]; then ln -s "$repo/skills/$s" "$stage/$s"; else cp -R "$repo/skills/$s" "$stage/$s"; fi
    backup=""
    if [[ -e "$target" || -L "$target" ]]; then
      backup=$(mktemp -d "$(dirname "$dest")/.skill-backup.XXXXXX")
      mv "$target" "$backup/$s"
      echo "backup: $backup/$s"
    fi
    if ! mv "$stage/$s" "$target"; then
      [[ -z "$backup" ]] || mv "$backup/$s" "$target"
      fail "could not install $target"
    fi
    rmdir "$stage"; stage=""
    echo "installed: $target"
  done
done
