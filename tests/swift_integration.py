#!/usr/bin/env python3
"""Real macOS/Xcode fixture for the XCTest-only runner. No app/device required."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/'skills/agentic-ios-game-workflow/scripts/run_tests.py'


def main():
    if sys.platform != 'darwin':
        print('SKIP: requires macOS/Xcode')
        return 0
    with tempfile.TemporaryDirectory(prefix="skill-swift-fixture-") as temp:
        # Exercise argument handling with both spaces and an apostrophe in the package path.
        package=Path(temp)/"Developer's Package"; tests=package/'Tests/EngineTests'
        tests.mkdir(parents=True)
        (package/'Package.swift').write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "Fixture", targets: [.testTarget(name: "EngineTests")])
''')
        source=tests/'Checks.swift'
        passing='''import XCTest
final class FirstTests: XCTestCase { func testOne() { XCTAssertTrue(true) } }
final class SecondTests: XCTestCase { func testTwo() { XCTAssertEqual(2, 2) } }
'''
        source.write_text(passing)
        env={**os.environ, 'CLANG_MODULE_CACHE_PATH':str(Path(temp)/'clang-cache')}
        def run(label,command,expected):
            result=subprocess.run(command,capture_output=True,text=True,env=env,timeout=180)
            if (result.returncode==0) != expected:
                print(result.stdout); print(result.stderr)
                raise AssertionError(f'{label}: unexpected status {result.returncode}')
            print(f'{label}: expected status {result.returncode}')
            return result
        runner=[sys.executable,str(RUNNER),'--debug','--package-path',str(package),'--shards','2']
        run('two XCTest classes and quoted path',runner,True)
        run('filtered XCTest',runner+['FirstTests','--skip-build'],True)
        for mode in ['--fast','release']:
            command=[item for item in runner if item!='--debug']
            if mode=='--fast': command.append(mode)
            run(f'XCTest {mode} configuration',command,True)
        run('unmatched filter',runner+['MissingTests','--skip-build'],False)
        source.write_text(passing.replace('XCTAssertTrue(true)','XCTAssertTrue(false)'))
        run('XCTest failure',runner,False)
        source.write_text(passing+'\nimport Testing\n@Test func modernFailure() { Issue.record("intentional fixture failure") }\n')
        mixed=run('mixed frameworks rejected',runner,False)
        assert 'Unsupported test discovery' in mixed.stderr, mixed.stderr
        run('SwiftPM executes failing modern test',['swift','test','--package-path',str(package),'--skip-build'],False)
        # Modern-only projects must also fail clearly rather than report zero successful tests.
        source.write_text('import Testing\n@Test func modernPass() {}\n')
        run('Swift Testing only rejected',runner,False)
    return 0

if __name__=='__main__':
    sys.exit(main())
