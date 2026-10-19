#!/usr/bin/env python3
"""Sharded SwiftPM test runner for engine packages with expensive shared fixtures.

`swift test --parallel` launches one process per test, so every test rebuilds the shared
live-scene fixtures (compiled scene, terrain, structures) from scratch. This runner builds the
tests optimized and runs whole test classes in a few long-lived shard processes, so each
fixture is built once per shard.

XCTest only: fails if discovery includes Swift Testing or an unknown name format.
Use standard `swift test` for mixed-framework packages. Requires macOS, Xcode and Python 3.14.
Run it from the package root (or pass --package-path).

Usage:
  run_tests.py                 # build (release) + run everything
  run_tests.py Terrain Player  # only classes whose name contains a pattern
  run_tests.py --fast          # optimized incremental build: debug config + -O in .build/fast
                                       # measure compile/runtime tradeoffs for your package
  run_tests.py --debug         # unoptimized build (faster to compile, slower to run)
  run_tests.py --shards 6 --skip-build
"""
import argparse
import collections
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.getcwd()
TIMINGS = os.path.join(ROOT, ".build", "test-class-timings.json")


def swift(config, *args, **kwargs):
    if config == "fast":
        # Debug configuration compiles incrementally and in parallel; -O keeps test runtime
        # close to release. A separate scratch path avoids invalidating the WMO release build.
        cmd = ["swift", *args, "-c", "debug", "--scratch-path", os.path.join(ROOT, ".build", "fast"), "-Xswiftc", "-O"]
    else:
        cmd = ["swift", *args, "-c", config]
    if config == "release":
        cmd += ["-Xswiftc", "-enable-testing"]
    return subprocess.run(cmd, cwd=ROOT, **kwargs)


def list_tests(config):
    out = swift(config, "test", "list", "--skip-build", capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(out.stderr or out.stdout)
    classes = collections.OrderedDict()
    unsupported = []
    for line in out.stdout.splitlines():
        m = re.match(r"^([\w]+)\.([\w]+)/(\w+)$", line.strip())
        if m:
            classes.setdefault(f"{m.group(1)}.{m.group(2)}", []).append(m.group(3))
        elif line.strip():
            unsupported.append(line.strip())
    if unsupported:
        sys.exit("Unsupported test discovery (XCTest-only helper); use swift test.\n" + "\n".join(unsupported[:10]))
    return classes


def shard(classes, count):
    try:
        with open(TIMINGS) as f:
            weights = json.load(f)
    except (OSError, ValueError):
        weights = {}
    shards = [[0.0, []] for _ in range(count)]
    for name in sorted(classes, key=lambda c: -weights.get(c, len(classes[c]))):
        target = min(shards, key=lambda s: s[0])
        target[0] += weights.get(name, len(classes[name]))
        target[1].append(name)
    return [s[1] for s in shards if s[1]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("patterns", nargs="*")
    parser.add_argument("--shards", type=int, default=max(2, min(8, (os.cpu_count() or 8) // 2)))
    parser.add_argument("--skip-build", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--debug", action="store_true")
    mode.add_argument("--fast", action="store_true")
    parser.add_argument("--package-path", help="SwiftPM package root (default: current directory)")
    args = parser.parse_args()
    if args.shards < 1:
        parser.error("--shards must be positive")
    global ROOT, TIMINGS
    if args.package_path:
        ROOT = os.path.abspath(args.package_path)
        TIMINGS = os.path.join(ROOT, ".build", "test-class-timings.json")
    config = "fast" if args.fast else "debug" if args.debug else "release"

    started = time.time()
    if not args.skip_build:
        print(f"building tests ({config})...", flush=True)
        if swift(config, "build", "--build-tests").returncode != 0:
            return 1

    classes = list_tests(config)
    if args.patterns:
        classes = collections.OrderedDict(
            (c, t) for c, t in classes.items() if any(p in c for p in args.patterns)
        )
    if not classes:
        print("no matching test classes")
        return 1
    groups = shard(classes, args.shards)
    total = sum(len(t) for t in classes.values())
    print(f"running {total} tests in {len(classes)} classes across {len(groups)} shards", flush=True)
    tests_started = time.time()

    path_result = swift(config, "build", "--show-bin-path", capture_output=True, text=True)
    if path_result.returncode:
        sys.exit(path_result.stderr or "could not locate test products")
    bin_path = path_result.stdout.strip()
    bundles = {b[: -len(".xctest")]: os.path.join(bin_path, b) for b in os.listdir(bin_path) if b.endswith(".xctest")}
    if not bundles:
        sys.exit(f"no .xctest bundle in {bin_path}")
    fallback = next(iter(bundles.values()))

    # Run bundles directly with xctest: `swift test` holds the .build lock, which would
    # serialize the shards.
    jobs = []
    os.makedirs(os.path.join(ROOT, ".build", "test-shards"), exist_ok=True)
    for index, group in enumerate(groups):
        by_bundle = collections.defaultdict(list)
        for name in group:
            by_bundle[bundles.get(name.split(".")[0], fallback)].append(name)
        log_path = os.path.join(ROOT, ".build", "test-shards", f"shard-{index}.log")
        jobs.append((by_bundle, log_path, group))

    def run_shard(job):
        by_bundle, log_path, group = job
        code = 0
        with open(log_path, "w") as log:
            for bundle, names in by_bundle.items():
                result = subprocess.run(["xcrun", "xctest", "-XCTest", ",".join(names), bundle],
                                        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                if result.returncode:
                    code = result.returncode
                    break
        return code, log_path, group

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        outcomes = list(pool.map(run_shard, jobs))

    failures, class_time = [], collections.Counter()
    case_re = re.compile(r"Test Case '-\[(\w+)\.(\w+) (\w+)\]' (passed|failed) \(([\d.]+) seconds\)")
    started_re = re.compile(r"Test Case '-\[(\w+)\.(\w+) (\w+)\]' started")
    exit_code = 0
    for returncode, log_path, group in outcomes:
        with open(log_path) as f:
            text = f.read()
        shard_failures = 0
        finished_cases = set()
        for module, cls, test, status, seconds in case_re.findall(text):
            class_time[f"{module}.{cls}"] += float(seconds)
            finished_cases.add((module, cls, test))
            if status == "failed":
                failures.append(f"{module}.{cls}/{test}")
                shard_failures += 1
        expected = {(module, cls, test) for name in group
                    for module, cls in [name.split(".", 1)] for test in classes[name]}
        missing = expected - finished_cases
        unexpected = finished_cases - expected
        if missing or unexpected:
            exit_code = 1
            failures.extend(f"{m}.{c}/{t} (not completed)" for m, c, t in sorted(missing))
            print(f"test coverage mismatch: {len(missing)} missing, {len(unexpected)} unexpected; {log_path}")
        if returncode != 0 and not shard_failures:
            exit_code = 1
            crashed = [c for c in started_re.findall(text) if c not in finished_cases]
            for module, cls, test in crashed:
                failures.append(f"{module}.{cls}/{test} (crashed)")
            print(f"shard crashed or failed to run: {log_path}")

    if not args.patterns and not failures and not exit_code:
        with open(TIMINGS, "w") as f:
            json.dump(class_time, f, indent=0, sort_keys=True)

    ran = sum(1 for _ in class_time)
    finished = time.time()
    print(
        f"\n{ran} classes finished in {finished - tests_started:.0f}s "
        f"({finished - started:.0f}s including build); {len(failures)} failed"
    )
    for name in failures:
        print(f"  FAIL {name}")
    if failures:
        print(f"shard logs: {os.path.join(ROOT, '.build', 'test-shards')}")
        return 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
