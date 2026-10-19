#!/bin/bash
# Release Simulator smoke for an iOS game: build, install, launch, then screenshot or video.
#
# usage: sim_smoke.sh [--no-build] [--video SECONDS] [--wait SECONDS] [--until REGEX] OUT_PREFIX [KEY=VALUE ...]
#
# Required environment:
#   SCHEME        Xcode scheme to build (also the .app name unless APP_NAME is set)
#   BUNDLE_ID     app bundle identifier
# Optional environment:
#   PROJECT       path to .xcodeproj (or WORKSPACE for .xcworkspace); default: the one in the cwd
#   APP_NAME      product name of the .app (default: $SCHEME)
#   SIMULATOR     UDID or "booted" (default booted)
#   DERIVED_DATA  build output (default /tmp/DD-$SCHEME); use a private one per parallel agent
#   SIM_DISPLAY   capture display for multi-display devices (e.g. "primary")
#   APP_ENV_PREFIX  e.g. MYGAME_; DEBUG_X=V pairs become ${APP_ENV_PREFIX}DEBUG_X=V and any
#                 ${APP_ENV_PREFIX}* variables in this script's environment are forwarded
#
# Outputs: OUT_PREFIX.log (console), OUT_PREFIX.png or OUT_PREFIX.mp4, OUT_PREFIX.build.log
# The screenshot is taken after --wait seconds (default 60), or as soon as the log matches --until.
# Simulator output is functional/visual evidence only, never performance or thermal evidence.
set -euo pipefail

build=1 video=0 wait=60 until=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) build=0; shift ;;
    --video) video="$2"; shift 2 ;;
    --wait) wait="$2"; shift 2 ;;
    --until) until="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) break ;;
  esac
done
out="${1:?usage: sim_smoke.sh [--no-build] [--video S] [--wait S] [--until REGEX] OUT_PREFIX [KEY=VALUE ...]}"
shift
: "${SCHEME:?set SCHEME}" "${BUNDLE_ID:?set BUNDLE_ID}"
app_name="${APP_NAME:-$SCHEME}"
sim="${SIMULATOR:-booted}"
dd="${DERIVED_DATA:-/tmp/DD-$SCHEME}"
prefix="${APP_ENV_PREFIX:-}"
mkdir -p "$(dirname "$out")"

if [[ $build -eq 1 ]]; then
  container=()
  [[ -n "${WORKSPACE:-}" ]] && container=(-workspace "$WORKSPACE")
  [[ -n "${PROJECT:-}" ]] && container=(-project "$PROJECT")
  start=$(date +%s)
  if ! xcodebuild "${container[@]+"${container[@]}"}" -scheme "$SCHEME" -configuration Release \
      -destination 'generic/platform=iOS Simulator' -derivedDataPath "$dd" \
      CODE_SIGNING_ALLOWED=NO build > "$out.build.log" 2>&1; then
    grep -E "error:" "$out.build.log" | sort -u | head -40
    echo "build failed; see $out.build.log" >&2
    exit 1
  fi
  echo "build ok in $(( $(date +%s) - start )) s"
fi

app=$(find "$dd/Build/Products" -maxdepth 3 -name "$app_name.app" | head -1)
[[ -n "$app" ]] || { echo "no $app_name.app under $dd" >&2; exit 1; }
xcrun simctl terminate "$sim" "$BUNDLE_ID" 2>/dev/null || true
xcrun simctl uninstall "$sim" "$BUNDLE_ID" 2>/dev/null || true
xcrun simctl install "$sim" "$app"

args=()
if [[ -n "$prefix" ]]; then
  while IFS= read -r kv; do args+=("$kv"); done < <(env | grep -E "^${prefix}[A-Z0-9_]+=" || true)
fi
for kv in "$@"; do
  [[ -n "$prefix" && "$kv" == DEBUG_*=* ]] && kv="${prefix}$kv"
  args+=("$kv")
done
for kv in "${args[@]+"${args[@]}"}"; do
  export "SIMCTL_CHILD_$kv"
  echo "app env: $kv"
done

if [[ "$video" != 0 ]]; then
  rm -f "$out.mp4"
  xcrun simctl io "$sim" recordVideo --codec h264 ${SIM_DISPLAY:+--display="$SIM_DISPLAY"} --force "$out.mp4" >/dev/null 2>&1 &
  recorder=$!
fi
xcrun simctl launch --console-pty "$sim" "$BUNDLE_ID" > "$out.log" 2>&1 &
launcher=$!

if [[ "$video" != 0 ]]; then
  sleep "$video"
  kill -INT "$recorder"
  wait "$recorder" 2>/dev/null || true
  echo "video: $out.mp4"
else
  if [[ -n "$until" ]]; then
    start=$SECONDS
    while (( SECONDS - start < wait )); do
      if grep -Eq "$until" "$out.log" 2>/dev/null; then
        sleep 3  # let trailing lines land
        echo "stopped after $((SECONDS - start)) s: log matched '$until'"
        break
      fi
      sleep 2
    done
  else
    sleep "$wait"
  fi
  xcrun simctl io "$sim" screenshot --mask=ignored ${SIM_DISPLAY:+--display="$SIM_DISPLAY"} "$out.png" >/dev/null
  echo "screenshot: $out.png"
fi
kill "$launcher" 2>/dev/null || true
echo "log: $out.log"
