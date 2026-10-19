#!/bin/bash
# Build/install/launch a Simulator app and capture a screenshot or video.
# Usage: sim_smoke.sh [--no-build] [--reset] [--wait SECONDS] [--until REGEX]
#                     [--video SECONDS] OUT_PREFIX [KEY=VALUE ...]
# Required: SCHEME, BUNDLE_ID. Optional: PROJECT or WORKSPACE, APP_NAME, SIMULATOR
# (default booted), DERIVED_DATA, SIM_DISPLAY, APP_ENV_PREFIX.
# --reset uninstalls first, deleting app data. Default install preserves existing data.
# --until must match within --wait (default 60); incompatible with --video.
# --video records a positive integer duration. --wait is a positive integer.
# Product: DERIVED_DATA/Build/Products/Release-iphonesimulator/APP_NAME.app.
# The script terminates its launched app on exit. Use an exclusively owned simulator slot.
# Outputs: OUT.log, OUT.png or OUT.mp4, OUT.build.log (when built).
# Exit 0 confirms launch stayed attached and capture succeeded, plus any requested marker.
# A marker's meaning is defined by the app; pixels/performance still need separate review.
set -euo pipefail
fail() { echo "$*" >&2; exit 1; }
value() { [[ $# -ge 2 && -n "$2" ]] || fail "missing value for $1"; }
build=1 reset=0 video=0 wait_seconds=60 until=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) build=0; shift ;;
    --reset) reset=1; shift ;;
    --video) value "$@"; [[ "$2" =~ ^[1-9][0-9]*$ ]] || fail "--video must be positive"; video="$2"; shift 2 ;;
    --wait) value "$@"; wait_seconds="$2"; shift 2 ;;
    --until) value "$@"; until="$2"; shift 2 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    --*) fail "unknown option: $1" ;;
    *) break ;;
  esac
done
[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || fail '--wait must be a positive integer'
[[ "$video" == 0 || "$video" =~ ^[1-9][0-9]*$ ]] || fail '--video must be a positive integer'
[[ "$video" == 0 || -z "$until" ]] || fail '--video and --until cannot be combined'
if [[ -n "$until" ]]; then
  regex_status=0; grep -Eq -- "$until" <<< '' || regex_status=$?
  [[ $regex_status -lt 2 ]] || fail 'invalid --until regex'
fi
out="${1:?provide OUT_PREFIX}"; shift
: "${SCHEME:?set SCHEME}" "${BUNDLE_ID:?set BUNDLE_ID}"
[[ -z "${PROJECT:-}" || -z "${WORKSPACE:-}" ]] || fail 'set PROJECT or WORKSPACE, not both'
app_name="${APP_NAME:-$SCHEME}"; sim="${SIMULATOR:-booted}"
dd="${DERIVED_DATA:-/tmp/DD-$SCHEME}"; prefix="${APP_ENV_PREFIX:-}"
[[ -z "$prefix" || "$prefix" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || fail 'invalid APP_ENV_PREFIX'
args=()
if [[ -n "$prefix" ]]; then
  while IFS= read -r kv; do
    [[ "$kv" != "$prefix"* ]] || args+=("$kv")
  done < <(env)
fi
for kv in "$@"; do
  [[ "$kv" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || fail "expected KEY=VALUE"
  [[ -z "$prefix" || "$kv" != DEBUG_*=* ]] || kv="${prefix}$kv"
  args+=("$kv")
done
for kv in "${args[@]+"${args[@]}"}"; do
  export "SIMCTL_CHILD_$kv"
  echo "forwarding app env: ${kv%%=*}" # Values may contain credentials; never echo them.
done
mkdir -p "$(dirname "$out")"
if [[ $build -eq 1 ]]; then
  container=()
  [[ -z "${WORKSPACE:-}" ]] || container=(-workspace "$WORKSPACE")
  [[ -z "${PROJECT:-}" ]] || container=(-project "$PROJECT")
  if ! xcodebuild "${container[@]+"${container[@]}"}" -scheme "$SCHEME" -configuration Release \
      -destination 'generic/platform=iOS Simulator' -derivedDataPath "$dd" \
      CODE_SIGNING_ALLOWED=NO build > "$out.build.log" 2>&1; then
    grep -E 'error:' "$out.build.log" | head -40 || true
    fail "build failed; see $out.build.log"
  fi
fi
app="$dd/Build/Products/Release-iphonesimulator/$app_name.app"
[[ -d "$app" ]] || fail "app not found: $app (use APP_NAME/DERIVED_DATA for custom products)"
xcrun simctl terminate "$sim" "$BUNDLE_ID" 2>/dev/null || true
if [[ $reset -eq 1 ]]; then xcrun simctl uninstall "$sim" "$BUNDLE_ID" 2>/dev/null || true; fi
xcrun simctl install "$sim" "$app"
launcher="" recorder=""
cleanup() {
  if [[ -n "$recorder" ]]; then kill -INT "$recorder" 2>/dev/null || true; wait "$recorder" 2>/dev/null || true; fi
  if [[ -n "$launcher" ]]; then
    xcrun simctl terminate "$sim" "$BUNDLE_ID" >/dev/null 2>&1 || true
    kill "$launcher" 2>/dev/null || true; wait "$launcher" 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
check_launch() {
  if ! kill -0 "$launcher" 2>/dev/null; then
    status=0; wait "$launcher" || status=$?
    fail "app launch/console exited early (status $status); see $out.log"
  fi
}
xcrun simctl launch --console-pty "$sim" "$BUNDLE_ID" > "$out.log" 2>&1 &
launcher=$!
display=(); [[ -z "${SIM_DISPLAY:-}" ]] || display=("--display=$SIM_DISPLAY")
if [[ "$video" != 0 ]]; then
  rm -f "$out.mp4"
  xcrun simctl io "$sim" recordVideo --codec h264 "${display[@]+"${display[@]}"}" --force "$out.mp4" > "$out.capture.log" 2>&1 &
  recorder=$!
  duration=$video
else duration=$wait_seconds
fi
start=$SECONDS; matched=0
while (( SECONDS - start < duration )); do
  check_launch
  if [[ -n "$recorder" ]] && ! kill -0 "$recorder" 2>/dev/null; then fail "recorder exited early; see $out.capture.log"; fi
  if [[ -n "$until" ]] && grep -Eq -- "$until" "$out.log"; then matched=1; break; fi
  sleep 0.2
done
check_launch
if [[ -n "$until" && $matched -eq 0 ]]; then fail "timed out waiting for log marker; see $out.log"; fi
if [[ -n "$recorder" ]]; then
  kill -INT "$recorder"
  if ! wait "$recorder"; then recorder=""; fail "video recording failed; see $out.capture.log"; fi
  recorder=""; [[ -s "$out.mp4" ]] || fail 'video output is empty'
  echo "video: $out.mp4"
else
  rm -f "$out.png"
  xcrun simctl io "$sim" screenshot --mask=ignored "${display[@]+"${display[@]}"}" "$out.png"
  [[ -s "$out.png" ]] || fail 'screenshot output is empty'
  check_launch
  echo "screenshot: $out.png"
fi
echo "log: $out.log"
