from __future__ import annotations
import os
import shlex
import stat
import sys
from typing import Optional, Tuple
from . import git
from .engine import analyze
MARKER = '# git-smart-commit managed hook'
HOOK_NAME = 'prepare-commit-msg'
SKIP_SOURCES = {'merge', 'squash', 'commit'}

def hooks_dir(cwd: Optional[str]=None) -> str:
    out = git.run_git(['rev-parse', '--git-path', 'hooks'], cwd=cwd).strip()
    return os.path.abspath(os.path.join(cwd or os.getcwd(), out))

def render_script(python: str) -> str:
    return '#!/bin/sh\n%s\nPY=%s\nif [ -x "$PY" ]; then\n  "$PY" -m git_smart_commit hook "$@" || true\nelif command -v git-smart-commit >/dev/null 2>&1; then\n  git-smart-commit hook "$@" || true\nfi\nexit 0\n' % (MARKER, shlex.quote(python or ''))

def install(cwd: Optional[str]=None, force: bool=False) -> Tuple[bool, str]:
    d = hooks_dir(cwd)
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, HOOK_NAME)
    note = ''
    if os.path.exists(target):
        with open(target, encoding='utf-8', errors='replace') as fh:
            ours = MARKER in fh.read()
        if not ours:
            if not force:
                return (False, 'A different %s hook already exists at %s.\nRe-run with --force to back it up and replace it.' % (HOOK_NAME, target))
            backup = target + '.bak'
            n = 1
            while os.path.exists(backup):
                n += 1
                backup = '%s.bak%d' % (target, n)
            os.replace(target, backup)
            note = '\nExisting hook backed up to %s' % backup
    with open(target, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(render_script(sys.executable))
    os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return (True, 'Installed %s hook at %s%s' % (HOOK_NAME, target, note))

def uninstall(cwd: Optional[str]=None) -> Tuple[bool, str]:
    target = os.path.join(hooks_dir(cwd), HOOK_NAME)
    if not os.path.exists(target):
        return (True, 'No %s hook installed.' % HOOK_NAME)
    with open(target, encoding='utf-8', errors='replace') as fh:
        if MARKER not in fh.read():
            return (False, 'The existing %s hook was not installed by git-smart-commit; leaving it alone.' % HOOK_NAME)
    os.remove(target)
    backup = target + '.bak'
    if os.path.exists(backup):
        os.replace(backup, target)
        return (True, 'Removed hook and restored your previous one from %s' % backup)
    return (True, 'Removed %s hook.' % HOOK_NAME)

def _has_user_content(text: str) -> bool:
    return any((l.strip() and (not l.startswith('#')) for l in text.splitlines()))

def run_hook(msg_file: str, source: Optional[str]=None, cwd: Optional[str]=None) -> int:
    if os.environ.get('GIT_SMART_SKIP') or source in SKIP_SOURCES:
        return 0
    try:
        root = git.repo_root(cwd)
        files = git.get_staged_files(root)
        if not files:
            return 0
        s = analyze(files, root)
        if s is None:
            return 0
        for w in s.warnings:
            print(w, file=sys.stderr)
        if source == 'message':
            return 0
        with open(msg_file, encoding='utf-8', errors='replace') as fh:
            original = fh.read()
        if _has_user_content(original):
            return 0
        out = s.subject + '\n'
        if git.cleanup_strips_comments(root):
            out += '\n# git-smart-commit: %d staged file(s), confidence: %s\n' % (len(files), s.confidence)
            for r in s.reasons:
                out += '#   - %s\n' % r
            for w in s.warnings:
                out += '#   %s\n' % w
        with open(msg_file, 'w', encoding='utf-8') as fh:
            fh.write(out + original)
    except Exception:
        return 0
    return 0