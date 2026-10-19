# Profiling commands

Replace `$DEVICE`, `$BUNDLE_ID`, `$APP` with your values. List devices with
`xcrun devicectl list devices` and `xcrun xctrace list devices`.

## Release build and install on a device

```bash
xcodebuild -scheme MyGame -configuration Release -destination "id=$DEVICE" \
  -derivedDataPath /tmp/mygame-device -allowProvisioningUpdates build
xcrun devicectl device install app --device "$DEVICE" \
  /tmp/mygame-device/Build/Products/Release-iphoneos/MyGame.app
xcrun devicectl device process launch --device "$DEVICE" --terminate-existing "$BUNDLE_ID"
```

Launch requires an available, unlocked device. If locked, report that condition and have the
owner unlock or launch it. Installation and process launch are separate evidence from gameplay.

## Metal System Trace

Find the app's current PID on the selected device first. Template names and exported schemas
vary by Xcode/device; inspect `xcrun xctrace list templates`, `record --help` and the export TOC.
The schema below is illustrative; use the one actually present in your trace.

```bash
xcrun xctrace record --template 'Metal System Trace' --device "$DEVICE" \
  --attach "$PID" --time-limit 60s --output /tmp/run.trace
xcrun xctrace export --input /tmp/run.trace --toc            # find table schemas
xcrun xctrace export --input /tmp/run.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="metal-gpu-intervals"]' > gpu.xml
```

Split GPU intervals by encoder label and by GPU performance state; label your encoders and
command buffers (`encoder.label = "CSM cascade 2"`) so the export is readable.

## Metal Performance HUD

Set `MTL_HUD_ENABLED=1` in the scheme environment (or enable it in Developer settings on the
device). Useful for a quick fps/GPU-time read, not for A/B numbers.

## Signposts

Emit `os_signpost` intervals for authority tick, plan build, encode and each pass behind an env
flag so Instruments' Points of Interest lines up CPU and GPU work. Keep them off for FPS captures.

## Shader validation in debug

`MTL_SHADER_VALIDATION=1` and `MTL_DEBUG_LAYER=1` in the scheme for out-of-bounds and binding
errors. Never measure with them on.
