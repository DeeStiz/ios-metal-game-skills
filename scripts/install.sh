#!/bin/bash
# Install these skills for one or more coding agents by copying (or symlinking) skills/* into the
# folder each agent scans.
#
# usage: scripts/install.sh [--agent NAME]... [--project DIR] [--link] [--skill NAME]...
#   --agent    claude | codex | copilot | gemini | agents | all   (default: all)
#   --project  install into DIR's project-level folders instead of your home folder
#   --link     symlink instead of copy (updates follow `git pull`)
#   --skill    install only the named skill(s) (default: every skill)
#
# Folders used (user level / project level):
#   claude   ~/.claude/skills        DIR/.claude/skills
#   codex    ~/.agents/skills        DIR/.agents/skills   (older Codex builds: ~/.codex/skills)
#   copilot  ~/.copilot/skills       DIR/.github/skills
#   gemini   ~/.gemini/skills        DIR/.gemini/skills
#   agents   ~/.agents/skills        DIR/.agents/skills   (shared location several tools read)
# If your tool uses a different folder, copy skills/<name>/ there; the format is the same.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
agents=() skills=() project="" link=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) agents+=("$2"); shift 2 ;;
    --project) project="$(cd "$2" && pwd)"; shift 2 ;;
    --link) link=1; shift ;;
    --skill) skills+=("$2"); shift 2 ;;
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ ${#agents[@]} -gt 0 ]] || agents=(all)
[[ " ${agents[*]} " == *" all "* ]] && agents=(claude codex copilot gemini)
if [[ ${#skills[@]} -eq 0 ]]; then
  for d in "$repo"/skills/*/; do skills+=("$(basename "$d")"); done
fi

target_dir() {
  local agent="$1"
  if [[ -n "$project" ]]; then
    case "$agent" in
      claude) echo "$project/.claude/skills" ;;
      codex|agents) echo "$project/.agents/skills" ;;
      copilot) echo "$project/.github/skills" ;;
      gemini) echo "$project/.gemini/skills" ;;
      *) echo "unknown agent: $agent" >&2; exit 2 ;;
    esac
  else
    case "$agent" in
      claude) echo "$HOME/.claude/skills" ;;
      codex|agents) echo "$HOME/.agents/skills" ;;
      copilot) echo "$HOME/.copilot/skills" ;;
      gemini) echo "$HOME/.gemini/skills" ;;
      *) echo "unknown agent: $agent" >&2; exit 2 ;;
    esac
  fi
}

done_dirs=" "
for agent in "${agents[@]}"; do
  dest="$(target_dir "$agent")"
  [[ "$done_dirs" == *" $dest "* ]] && continue
  done_dirs+="$dest "
  mkdir -p "$dest"
  for s in "${skills[@]}"; do
    src="$repo/skills/$s"
    [[ -f "$src/SKILL.md" ]] || { echo "no such skill: $s" >&2; exit 2; }
    rm -rf "${dest:?}/$s"
    if [[ $link -eq 1 ]]; then ln -s "$src" "$dest/$s"; else cp -R "$src" "$dest/$s"; fi
  done
  echo "$agent: ${#skills[@]} skills -> $dest"
done
