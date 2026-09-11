import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'skills/sync-agent-rules/scripts/sync_rules.py'
spec = importlib.util.spec_from_file_location('sync_rules', SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='agent rules test ')
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'shared source'
        self.project = self.root / 'project with spaces'
        self.project.mkdir()
        self.source.mkdir()
        shutil.copy2(REPO / 'manifest.json', self.source / 'manifest.json')
        manifest = json.loads((REPO / 'manifest.json').read_text())
        for name in manifest['files']:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, target)
        self.agents = b'# Project\r\n\r\nKeep this exact text.\r\n'
        (self.project / 'AGENTS.md').write_bytes(self.agents)
        (self.project / 'TEAM_RULES.md').write_bytes(b'Project-specific authority.\n')

    def tearDown(self):
        self.temporary.cleanup()

    def run_sync(self, apply=True):
        with contextlib.redirect_stdout(io.StringIO()):
            return sync.sync(self.project, str(self.source), 'main', apply, False)

    def test_check_does_not_install(self):
        self.assertEqual(self.run_sync(False), 0)
        self.assertFalse((self.project / '.agents').exists())
        self.assertEqual((self.project / 'AGENTS.md').read_bytes(), self.agents)

    def test_install_and_repeat(self):
        self.assertEqual(self.run_sync(), 0)
        self.assertTrue((self.project / 'AGENTS.md').read_bytes().startswith(self.agents))
        self.assertEqual((self.project / 'TEAM_RULES.md').read_bytes(), b'Project-specific authority.\n')
        lock = self.project / sync.LOCK
        first = lock.read_bytes()
        stamp = lock.stat().st_mtime_ns
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual(lock.read_bytes(), first)
        self.assertEqual(lock.stat().st_mtime_ns, stamp)

    def test_update_preserves_project_edits_and_backs_up(self):
        self.run_sync()
        agents = self.project / 'AGENTS.md'
        agents.write_bytes(agents.read_bytes() + b'\r\nMy new project rule.\r\n')
        target = self.project / '.agents/shared/development.md'
        previous = target.read_bytes()
        source = self.source / 'rules/development.md'
        source.write_bytes(source.read_bytes() + b'\nNew shared rule.\n')
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual(target.read_bytes(), source.read_bytes())
        self.assertTrue(agents.read_bytes().endswith(b'My new project rule.\r\n'))
        copies = list((self.project / '.agents/shared/backups').rglob('development.md'))
        self.assertTrue(any(p.read_bytes() == previous for p in copies))

    def test_git_line_endings_do_not_create_conflict(self):
        self.run_sync()
        target = self.project / '.agents/shared/development.md'
        target.write_bytes(target.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        self.assertEqual(self.run_sync(), 0)

    def test_conflict_aborts_other_updates(self):
        self.run_sync()
        changed = self.project / '.agents/shared/development.md'
        changed.write_bytes(b'Local customization.\n')
        source = self.source / 'skills/competitor-research/SKILL.md'
        source.write_bytes(source.read_bytes() + b'\nIncoming change.\n')
        target = self.project / '.agents/skills/competitor-research/SKILL.md'
        before = target.read_bytes()
        old_lock = (self.project / sync.LOCK).read_bytes()
        self.assertEqual(self.run_sync(), 2)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual((self.project / sync.LOCK).read_bytes(), old_lock)
        self.assertEqual(changed.read_bytes(), b'Local customization.\n')

    def test_edited_managed_block_is_preserved(self):
        self.run_sync()
        agents = self.project / 'AGENTS.md'
        altered = agents.read_bytes().replace(b'## ', b'### ')
        agents.write_bytes(altered)
        self.assertEqual(self.run_sync(), 2)
        self.assertEqual(agents.read_bytes(), altered)

    def test_missing_managed_file_is_conflict(self):
        self.run_sync()
        (self.project / '.agents/shared/development.md').unlink()
        self.assertEqual(self.run_sync(), 2)

    def test_new_file_collision(self):
        target = self.project / '.agents/shared/development.md'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'Existing project file')
        self.assertEqual(self.run_sync(), 2)
        self.assertFalse((self.project / sync.LOCK).exists())

    def test_retired_file_not_deleted(self):
        manifest_path = self.source / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['files']['rules/extra.md'] = '.agents/shared/extra.md'
        (self.source / 'rules/extra.md').write_text('extra')
        manifest_path.write_text(json.dumps(manifest))
        self.run_sync()
        del manifest['files']['rules/extra.md']
        manifest_path.write_text(json.dumps(manifest))
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual((self.project / '.agents/shared/extra.md').read_text(), 'extra')

    def test_manifest_cannot_escape_project(self):
        manifest_path = self.source / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['files']['rules/development.md'] = '.agents/shared/../../outside.md'
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            self.run_sync()
        self.assertFalse((self.project / '.agents').exists())

    def test_failure_restores_previous_files(self):
        self.run_sync()
        before = (self.project / '.agents/shared/development.md').read_bytes()
        old_lock = (self.project / sync.LOCK).read_bytes()
        source = self.source / 'rules/development.md'
        source.write_bytes(source.read_bytes() + b'\nUpdate.\n')
        original_write = sync.atomic_write
        def fail_lock(path, data):
            if path == self.project / sync.LOCK:
                raise OSError('Injected disk write failure')
            return original_write(path, data)
        with patch.object(sync, 'atomic_write', side_effect=fail_lock):
            with self.assertRaises(OSError):
                self.run_sync()
        self.assertEqual((self.project / '.agents/shared/development.md').read_bytes(), before)
        self.assertEqual((self.project / sync.LOCK).read_bytes(), old_lock)

    def test_credentials_in_source_rejected(self):
        with self.assertRaises(ValueError):
            with sync.source_tree('https://secret@github.com/account/repo.git', 'main'):
                pass


if __name__ == '__main__':
    unittest.main()
