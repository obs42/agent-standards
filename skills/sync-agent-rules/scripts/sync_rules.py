"""Install a reviewed manifest; preserve project files and locally edited copies."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
import uuid

LOCK = '.agents/shared/lock.json'
DEFAULT_SOURCE = 'https://github.com/obs42/agent-standards.git'
BEGIN = '<!-- agent-standards:begin -->'
END = '<!-- agent-standards:end -->'
BLOCK = '''<!-- agent-standards:begin -->
## 共享规范

设计与工具交付参考 [.agents/shared/development.md](.agents/shared/development.md)，具体项目规则仍由本项目入口和 TEAM_RULES.md 明确。
模块文档维护用 [.agents/skills/module-registry/SKILL.md](.agents/skills/module-registry/SKILL.md)；竞品新结论用 [.agents/skills/competitor-research/SKILL.md](.agents/skills/competitor-research/SKILL.md)。按任务读取，不要求每次通读。
用户要求“同步共享规则”时，读取 [.agents/skills/sync-agent-rules/SKILL.md](.agents/skills/sync-agent-rules/SKILL.md)，按 lock 中的来源检查和更新。普通开发不自动联网同步。
<!-- agent-standards:end -->'''


def sha(data):
    # This bundle contains text files; Git's CRLF conversion is not a local edit.
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def safe_path(root, relative):
    name = PurePosixPath(relative)
    if (not relative or '\\' in relative or ':' in relative or name.is_absolute()
            or any(part in ('..', '.') for part in relative.split('/'))):
        raise ValueError('非法相对路径：' + relative)
    target = root.joinpath(*name.parts)
    # Reject links even when their current target is inside the project.
    for item in (target, *target.parents):
        if item == root:
            break
        if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
            raise ValueError('不通过链接或目录联接写入：' + str(item))
    if not target.resolve().is_relative_to(root):
        raise ValueError('路径超出目录：' + str(target))
    return target


def read_optional(path):
    return path.read_bytes() if path.exists() else None


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.sync-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def git(directory, *args):
    result = subprocess.run(['git', '-C', str(directory), *args], capture_output=True,
                            text=True, encoding='utf-8', timeout=90,
                            env=dict(os.environ, GIT_TERMINAL_PROMPT='0'))
    if result.returncode:
        raise RuntimeError('Git 读取失败；检查网络、仓库权限和 ref。\n' + result.stderr.strip())
    return result.stdout.strip()


@contextmanager
def source_tree(source, ref):
    local = Path(source).expanduser()
    if local.is_dir():
        yield local.resolve(), None
        return
    url = urlsplit(source)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('来源须为已存在的本地目录或不含凭据的 HTTPS Git 地址。')
    if not ref or ref.startswith('-') or any(c.isspace() for c in ref):
        raise ValueError('非法 Git ref。')
    with tempfile.TemporaryDirectory(prefix='agent-standards-source-') as temporary:
        checkout = Path(temporary).resolve()
        git(checkout, 'init', '--quiet')
        git(checkout, 'remote', 'add', 'origin', source)
        git(checkout, '-c', 'credential.interactive=false', 'fetch', '--depth=1', 'origin', ref)
        revision = git(checkout, 'rev-parse', 'FETCH_HEAD')
        git(checkout, '-c', 'core.hooksPath=/dev/null', 'checkout', '--quiet', '--detach', revision)
        yield checkout, revision


def desired_files(source):
    manifest = json.loads(safe_path(source, 'manifest.json').read_text(encoding='utf-8-sig'))
    if manifest.get('schema') != 1 or manifest.get('bundle') != 'agent-standards':
        raise ValueError('不支持的共享清单。')
    mapping = manifest.get('files')
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('清单缺少 files。')
    output = {}
    seen_targets = set()
    for source_name, target in mapping.items():
        if not isinstance(target, str) or not (target.startswith('.agents/skills/')
                or target.startswith('.agents/shared/')):
            raise ValueError('清单只能安装到项目 .agents/skills 或 .agents/shared。')
        if target == LOCK or target.startswith('.agents/shared/backups/') or target == '.agents/shared/.gitignore':
            raise ValueError('清单不能写同步器元数据。')
        safe_path(source, target)  # Validate syntax even before a target project exists.
        if target.casefold() in seen_targets:
            raise ValueError('清单包含重复目标：' + target)
        seen_targets.add(target.casefold())
        output[target] = safe_path(source, source_name).read_bytes()
    required = {'.agents/shared/development.md',
                '.agents/skills/module-registry/SKILL.md',
                '.agents/skills/competitor-research/SKILL.md',
                '.agents/skills/sync-agent-rules/SKILL.md',
                '.agents/skills/sync-agent-rules/scripts/sync_rules.py'}
    if not required.issubset(output):
        raise ValueError('清单缺少项目入口引用的必需文件。')
    output['.agents/shared/.gitignore'] = b'backups/\n'
    fingerprint = sha(json_bytes({key: sha(value) for key, value in sorted(output.items())}))
    return output, fingerprint


def agents_content(current):
    text = (current or b'').decode('utf-8')
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError('AGENTS.md 的共享标记不完整或重复，保留原文件。')
    newline = '\r\n' if '\r\n' in text else '\n'
    replacement = BLOCK.replace('\n', newline)
    if BEGIN in text:
        first, last = text.index(BEGIN), text.index(END) + len(END)
        if first >= last:
            raise ValueError('AGENTS.md 的共享标记顺序错误。')
        old_block = text[first:last].encode('utf-8')
        merged = text[:first] + replacement + text[last:]
    else:
        old_block = None
        merged = text + (newline * 2 if text and not text.endswith(newline * 2) else '') + replacement + newline
    return merged.encode('utf-8'), old_block, replacement.encode('utf-8')


def sync(project, source, ref, apply=False, diff=True):
    project = project.resolve()
    if not project.is_dir():
        raise ValueError('目标项目目录不存在。')
    lock_path = safe_path(project, LOCK)
    old_lock_bytes = read_optional(lock_path)
    lock = json.loads(old_lock_bytes.decode('utf-8-sig')) if old_lock_bytes else {}
    if lock and (lock.get('schema') != 1 or lock.get('bundle') != 'agent-standards'):
        raise ValueError('现有 lock 格式不受支持，未覆盖。')
    source = source or lock.get('source') or DEFAULT_SOURCE
    ref = ref or lock.get('ref', 'main')
    if not source:
        raise ValueError('首次安装需要 --source；未找到已配置的共享来源。')
    if Path(source).expanduser().is_dir():
        source = str(Path(source).expanduser().resolve())
    with source_tree(source, ref) as (checkout, revision):
        if checkout == project:
            raise ValueError('共享源与安装项目不能相同。')
        wanted, fingerprint = desired_files(checkout)
    revision = revision or 'snapshot:' + fingerprint
    previous = lock.get('files', {})
    changes, baseline, conflicts = {}, {LOCK: old_lock_bytes}, []
    records = dict(previous)
    for target, incoming in wanted.items():
        path = safe_path(project, target)
        current = read_optional(path)
        baseline[target] = current
        if current != incoming and (current is None or sha(current) != sha(incoming)):
            expected = previous.get(target)
            if (current is not None and (expected is None or sha(current) != expected)) or (current is None and expected):
                conflicts.append(target)
            else:
                changes[target] = incoming
        records[target] = sha(incoming)
    agents_path = safe_path(project, 'AGENTS.md')
    current_agents = read_optional(agents_path)
    new_agents, old_block, new_block = agents_content(current_agents)
    baseline['AGENTS.md'] = current_agents
    block_hash = lock.get('agents_block')
    if old_block != new_block:
        if (old_block is not None and (not block_hash or sha(old_block) != block_hash)) or (old_block is None and block_hash):
            conflicts.append('AGENTS.md（共享区块）')
        else:
            changes['AGENTS.md'] = new_agents
    retired = sorted(set(previous) - set(wanted))
    result_lock = {'schema': 1, 'bundle': 'agent-standards', 'source': source, 'ref': ref,
                   'revision': revision, 'snapshot': fingerprint, 'files': records,
                   'retired': retired, 'agents_block': sha(new_block)}
    print('来源：' + source + '\n版本：' + revision)
    for target, incoming in changes.items():
        print(('新增：' if baseline[target] is None else '更新：') + target)
        if diff:
            before = (baseline[target] or b'').decode('utf-8', errors='replace').splitlines(True)
            after = incoming.decode('utf-8', errors='replace').splitlines(True)
            print(''.join(difflib.unified_diff(before, after, fromfile=target, tofile=target + ' (incoming)')), end='')
    for target in retired:
        print('清单已移除，保留本地文件：' + target)
    if conflicts:
        print('本地内容有修改；整次更新未写入：\n' + '\n'.join(conflicts))
        if diff:
            for target in conflicts:
                if target in wanted:
                    before = (baseline[target] or b'').decode('utf-8', errors='replace').splitlines(True)
                    after = wanted[target].decode('utf-8', errors='replace').splitlines(True)
                    print(''.join(difflib.unified_diff(before, after, fromfile=target + ' (local)',
                                                      tofile=target + ' (incoming)')), end='')
        return 2
    if not apply:
        print(f'检查完成：{len(changes)} 个文件变化，未写入。')
        return 0
    new_lock_bytes = json_bytes(result_lock)
    if new_lock_bytes != old_lock_bytes:
        changes[LOCK] = new_lock_bytes
        baseline[LOCK] = old_lock_bytes
    if not changes:
        print('已是当前版本，无需更新。')
        return 0
    # Recheck all observed paths before any writes, including unchanged managed files.
    for target, before in baseline.items():
        if read_optional(safe_path(project, target)) != before:
            raise RuntimeError('检查期间文件变化，未开始安装：' + target)
    backup_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]
    backup_root = safe_path(project, '.agents/shared/backups/' + backup_id)
    for target in changes:
        if baseline[target] is not None:
            atomic_write(safe_path(backup_root, target), baseline[target])
    applied = []
    try:
        for target, incoming in changes.items():
            path = safe_path(project, target)
            if read_optional(path) != baseline[target]:
                raise RuntimeError('写入前文件变化：' + target)
            atomic_write(path, incoming)
            applied.append(target)
    except Exception:
        # Roll back only our own exact bytes; preserve concurrent edits.
        for target in reversed(applied):
            path = safe_path(project, target)
            if read_optional(path) == changes[target]:
                if baseline[target] is None:
                    path.unlink()
                else:
                    atomic_write(path, baseline[target])
        raise
    print(f'同步完成：{len(changes)} 个文件写入（含版本记录）；项目原规则保留。')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--source')
    parser.add_argument('--ref')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--summary', action='store_true', help='Omit text diffs')
    args = parser.parse_args()
    return sync(args.project, args.source, args.ref, args.apply, not args.summary)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('同步失败：' + str(error), file=sys.stderr)
        sys.exit(1)
