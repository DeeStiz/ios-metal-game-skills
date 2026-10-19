"""Behavioral fixtures use temp directories; never install globally or run a real simulator."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VRT = ROOT / 'skills/metal-visual-regression/scripts/vrt_compare.py'
RUNNER = ROOT / 'skills/agentic-ios-game-workflow/scripts/run_tests.py'
SMOKE = ROOT / 'skills/ios-game-simulator-automation/scripts/sim_smoke.sh'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class TempTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cmd(self, args, **kwargs):
        return subprocess.run(args, text=True, capture_output=True, timeout=30, **kwargs)


class VisualTests(TempTest):
    def setUp(self):
        super().setUp()
        self.base, self.cand = self.root / 'base', self.root / 'cand'
        self.base.mkdir(); self.cand.mkdir()

    def frame(self, folder, name='view.png', color=80, size=(49,49)):
        path = folder / name; path.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', size, (color,)*3).save(path)

    def compare(self, *options):
        return self.run_cmd([sys.executable, str(VRT), str(self.base), str(self.cand), *options])

    def report(self):
        return json.loads((self.cand / 'vrt-report/report.json').read_text())

    def test_identical_and_repeat_run_excludes_own_report(self):
        self.frame(self.base); self.frame(self.cand)
        self.assertEqual(self.compare().returncode, 0)
        self.assertEqual(self.compare().returncode, 0)
        self.assertEqual(len(self.report()['frames']), 1)

    def test_empty_missing_new_and_nonexistent(self):
        self.assertEqual(self.compare().returncode, 1)
        self.frame(self.base)
        self.assertEqual(self.compare().returncode, 1)
        self.frame(self.cand, 'new.png')
        self.assertEqual(self.compare().returncode, 1)
        self.assertIn('no accepted baseline', str(self.report()))
        self.base = self.root / 'absent'
        self.assertEqual(self.compare().returncode, 2)

    def test_partial_edge_tiles_are_compared(self):
        self.frame(self.base); self.frame(self.cand)
        path = self.cand/'view.png'
        with Image.open(path) as image:
            for n in range(49):
                image.putpixel((48,n),(255,255,255)); image.putpixel((n,48),(255,255,255))
            image.save(path)
        self.assertEqual(self.compare().returncode, 1)

    def test_tiny_image(self):
        self.frame(self.base,size=(1,1)); self.frame(self.cand,size=(1,1))
        self.assertEqual(self.compare().returncode, 0)
        self.frame(self.cand,color=240,size=(1,1))
        self.assertEqual(self.compare().returncode, 1)

    def test_invalid_tile_and_report_paths(self):
        for tile in ['0','-1']:
            self.assertEqual(self.compare('--tile',tile).returncode, 2)
        for path in [self.base, self.cand, self.root, self.base/'report']:
            self.assertEqual(self.compare('--out',str(path)).returncode, 2)

    def test_dimensions_and_corrupt_images_fail(self):
        self.frame(self.base); self.frame(self.cand,size=(50,49))
        self.assertEqual(self.compare().returncode, 1)
        (self.cand/'view.png').write_bytes(b'not an image')
        result=self.compare()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn('unreadable', str(self.report()))

    def test_sequence_gaps_duplicates_short_and_size_changes(self):
        for names in [('shot__s00.png',), ('shot__m00.png','shot__m02.png'),
                      ('shot__s0.png','shot__s00.png')]:
            with self.subTest(names=names):
                for folder in [self.base,self.cand]:
                    for p in folder.glob('*.png'): p.unlink()
                    for name in names: self.frame(folder,name)
                self.assertEqual(self.compare().returncode,1)
        for folder in [self.base,self.cand]:
            for p in folder.glob('*.png'): p.unlink()
            self.frame(folder,'shot__s00.png')
            self.frame(folder,'shot__s01.png',size=(50,50))
        result=self.compare()
        self.assertEqual(result.returncode,1)
        self.assertNotIn('Traceback', result.stderr)

    def test_static_and_motion_sequences(self):
        for folder in [self.base,self.cand]:
            for kind in ['s','m']:
                for n in range(3): self.frame(folder,f'shot__{kind}{n:02}.png')
        self.assertEqual(self.compare().returncode,0)
        self.frame(self.cand,'shot__s01.png',color=140)
        self.frame(self.cand,'shot__m01.png',color=140)
        self.assertEqual(self.compare().returncode,1)
        self.assertIn('static-flicker',str(self.report()))
        self.assertIn('z-fight',str(self.report()))

    def test_tile_statistics_use_actual_edge_pixels(self):
        vrt=module('vrt',VRT)
        a=np.zeros((25,25)); a[24,:]=100; a[:,24]=100
        np.testing.assert_array_equal(vrt.tiles(a), [[0,100],[100,100]])


class InstallerTests(TempTest):
    def install(self,*args):
        return self.run_cmd(['bash',str(ROOT/'scripts/install.sh'),'--project',str(self.root),*args])

    def test_copy_preserve_replace_and_backup(self):
        args=['--agent','codex','--skill','metal-frame-pacing']
        self.assertEqual(self.install(*args).returncode,0)
        dest=self.root/'.agents/skills/metal-frame-pacing'
        (dest/'custom.txt').write_text('local change')
        self.assertEqual(self.install(*args).returncode,0)
        self.assertTrue((dest/'custom.txt').exists())
        self.assertEqual(self.install(*args,'--replace','--link').returncode,0)
        self.assertTrue(dest.is_symlink())
        backups=list((self.root/'.agents').glob('.skill-backup.*/metal-frame-pacing/custom.txt'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_text(),'local change')

    def test_invalid_request_is_preflighted(self):
        for args in [('--skill','metal-frame-pacing','--skill','missing'),
                     ('--skill','../metal-frame-pacing'),('--agent','all','--agent','unknown'),
                     ('--skill',),('--agent',)]:
            self.assertNotEqual(self.install(*args).returncode,0)
            self.assertFalse((self.root/'.agents').exists())

    def test_all_agents_and_duplicate_destination(self):
        result=self.install('--agent','all','--skill','game-level-data')
        self.assertEqual(result.returncode,0,result.stderr)
        for folder in ['.claude','.agents','.github','.gemini']:
            self.assertTrue((self.root/folder/'skills/game-level-data/SKILL.md').is_file())
        result=self.install('--agent','codex','--agent','agents','--skill','game-level-data')
        self.assertEqual(result.stdout.count('preserved existing:'),1)

    def test_dangling_symlink_preserved_then_backed_up(self):
        dest=self.root/'.agents/skills/metal-frame-pacing'
        dest.parent.mkdir(parents=True); dest.symlink_to(self.root/'absent')
        args=['--agent','codex','--skill','metal-frame-pacing']
        self.assertEqual(self.install(*args).returncode,0)
        self.assertTrue(dest.is_symlink())
        self.assertEqual(self.install(*args,'--replace').returncode,0)
        self.assertFalse(dest.is_symlink())
        self.assertEqual(len(list((self.root/'.agents').glob('.skill-backup.*/metal-frame-pacing'))),1)


MOCK_XCRUN = r'''
import json, os, signal, sys, time
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['MOCK_LOG'],'a') as log:
    log.write(json.dumps({'args':args,'env':os.environ.get('SIMCTL_CHILD_GAME_DEBUG_SPAWN')})+'\n')
mode=os.environ.get('MOCK_MODE','ok')
if 'launch' in args:
    if mode=='launch-fail': sys.exit(42)
    if mode!='timeout': print('GAME_READY',flush=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True: time.sleep(.05)
elif 'recordVideo' in args:
    if mode=='video-fail': sys.exit(1)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    Path(args[-1]).write_bytes(b'video')
    while True: time.sleep(.05)
elif 'screenshot' in args:
    if mode=='capture-fail': sys.exit(1)
    if mode!='empty': Path(args[-1]).write_bytes(b'capture')
'''


class SmokeTests(TempTest):
    def setUp(self):
        super().setUp()
        mock=self.root/'bin'; mock.mkdir()
        command=mock/'xcrun'
        command.write_text('#!'+sys.executable+'\n'+MOCK_XCRUN); command.chmod(0o755)
        self.app=self.root/'dd/Build/Products/Release-iphonesimulator/MyGame.app'
        self.app.mkdir(parents=True)
        self.log=self.root/'calls.jsonl'
        self.env={**os.environ,'PATH':str(mock)+os.pathsep+os.environ['PATH'],
                  'SCHEME':'MyGame','BUNDLE_ID':'com.example.game','APP_ENV_PREFIX':'GAME_',
                  'DERIVED_DATA':str(self.root/'dd'),'MOCK_LOG':str(self.log)}

    def smoke(self,mode='ok',options=(),env_args=()):
        return self.run_cmd(['bash',str(SMOKE),'--no-build','--wait','1',*options,
                             str(self.root/'capture'),*env_args],env={**self.env,'MOCK_MODE':mode})

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_success_marker_environment_and_default_preserves_data(self):
        result=self.smoke(options=['--until','GAME_READY'],env_args=['DEBUG_SPAWN=1,2,3','TOKEN=private-value'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.root/'capture.png').is_file())
        self.assertNotIn('private-value',result.stdout)
        calls=self.calls()
        self.assertFalse(any('uninstall' in c['args'] for c in calls))
        self.assertEqual(next(c for c in calls if 'launch' in c['args'])['env'],'1,2,3')
        self.assertGreaterEqual(sum('terminate' in c['args'] for c in calls),2)

    def test_launch_failure_timeout_capture_failure_and_empty_output(self):
        for mode in ['launch-fail','timeout','capture-fail','empty']:
            with self.subTest(mode=mode):
                result=self.smoke(mode,options=['--until','GAME_READY'])
                self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertIn('timed out',self.smoke('timeout',options=['--until','GAME_READY']).stderr)

    def test_reset_is_explicit(self):
        result=self.smoke(options=['--reset','--until','GAME_READY'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(any('uninstall' in c['args'] for c in self.calls()))

    def test_video_success_failure_and_invalid_options(self):
        self.assertEqual(self.smoke(options=['--video','1']).returncode,0)
        self.assertNotEqual(self.smoke('video-fail',options=['--video','1']).returncode,0)
        for opts in [('--wait','0'),('--video','0'),('--video','-1'),('--until','['),('--video','1','--until','x')]:
            self.assertNotEqual(self.smoke(options=opts).returncode,0)

    def test_build_failure_without_error_line(self):
        build=self.root/'bin/xcodebuild'
        build.write_text('#!/bin/bash\necho build-stopped\nexit 9\n'); build.chmod(0o755)
        result=self.run_cmd(['bash',str(SMOKE),str(self.root/'capture')],env=self.env)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('build failed; see',result.stderr)
        self.assertFalse(self.log.exists())

    def test_exact_product_selection(self):
        self.app.rmdir()
        (self.root/'dd/Build/Products/Debug-iphonesimulator/MyGame.app').mkdir(parents=True)
        self.assertNotEqual(self.smoke().returncode,0)
        self.assertFalse(self.log.exists())


class ValidatorTests(TempTest):
    def setUp(self):
        super().setUp()
        self.validator=module('validator', ROOT/'scripts/validate_skills.py')
        self.skill=self.root/'skills/example'; self.skill.mkdir(parents=True)
        self.md=self.skill/'SKILL.md'
        self.md.write_text('---\nname: example\ndescription: >\n  A useful multi-line\n  description.\n---\nBody.\n')

    def test_yaml_multiline_and_valid_reference(self):
        (self.skill/'references').mkdir()
        (self.skill/'references/details.md').write_text('details')
        self.md.write_text(self.md.read_text()+'\n[details](references/details.md)\n')
        self.assertEqual(self.validator.validate(self.root),(1,[]))

    def test_missing_markdown_reference(self):
        self.md.write_text(self.md.read_text()+'\n[details](references/missing.md)\n')
        self.assertTrue(self.validator.validate(self.root)[1])

    def test_duplicate_invalid_yaml_and_name(self):
        for metadata in ['name: example\nname: example\ndescription: okay',
                         'name: example\ndescription: [broken',
                         'name: wrong\ndescription: okay',
                         'name: example\ndescription: 42']:
            self.md.write_text('---\n'+metadata+'\n---\n')
            self.assertTrue(self.validator.validate(self.root)[1])


class RunnerTests(TempTest):
    def setUp(self):
        super().setUp()
        self.runner=module('runner', RUNNER)

    def discovery(self,text):
        return patch.object(self.runner,'swift',return_value=subprocess.CompletedProcess([],0,text,''))

    def test_xctest_discovery(self):
        with self.discovery('EngineTests.WorldTests/testRestore\n'):
            self.assertEqual(self.runner.list_tests('debug'),{'EngineTests.WorldTests':['testRestore']})

    def test_mixed_and_unrecognized_discovery_rejected(self):
        for extra in ['EngineTests.modernFailure()','EngineTests.Suite/testThing()','unknown output']:
            with self.discovery('EngineTests.WorldTests/testRestore\n'+extra), self.assertRaises(SystemExit):
                self.runner.list_tests('debug')

    def test_invalid_shards(self):
        with patch.object(sys,'argv',['run_tests.py','--shards','0']), self.assertRaises(SystemExit):
            self.runner.main()

    def test_shard_missing_completion_and_crash_fail(self):
        product=self.root/"Developer's Products"; product.mkdir()
        (product/'Fixture.xctest').mkdir()
        discovery='EngineTests.WorldTests/testOne\nEngineTests.WorldTests/testTwo\n'
        def fake_swift(config,*args,**kwargs):
            output=discovery if args[:2]==('test','list') else str(product)
            return subprocess.CompletedProcess([],0,output,'')
        def outcome(completed,code):
            def execute(args,**kwargs):
                self.assertEqual(args[-1],str(product/'Fixture.xctest'))
                for name in completed:
                    kwargs['stdout'].write(f"Test Case '-[EngineTests.WorldTests {name}]' passed (0.001 seconds)\n")
                return subprocess.CompletedProcess(args,code)
            return execute
        for completed,code in [(['testOne'],0),([],1),(['testOne','testTwo'],0)]:
            with self.subTest(completed=completed,code=code), \
                 patch.object(self.runner,'swift',side_effect=fake_swift), \
                 patch.object(self.runner.subprocess,'run',side_effect=outcome(completed,code)), \
                 patch.object(sys,'argv',['runner','--skip-build','--package-path',str(self.root),'--shards','1']):
                status=self.runner.main()
                self.assertEqual(status==0,len(completed)==2 and code==0)



if __name__=='__main__':
    unittest.main()
