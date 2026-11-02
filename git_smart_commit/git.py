from __future__ import annotations
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
MAX_DIFF_CHARS = 2000000

class GitError(RuntimeError):
    pass

def run_git(args: Sequence[str], cwd: Optional[str]=None) -> str:
    try:
        proc = subprocess.run(['git', *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise GitError('git executable not found on PATH')
    if proc.returncode != 0:
        msg = proc.stderr.decode('utf-8', 'replace').strip()
        raise GitError(msg or 'git %s failed' % ' '.join(args))
    return proc.stdout.decode('utf-8', 'replace')

def repo_root(cwd: Optional[str]=None) -> str:
    try:
        return run_git(['rev-parse', '--show-toplevel'], cwd=cwd).strip()
    except GitError:
        raise GitError('not inside a git working tree')

@dataclass
class StagedFile:
    status: str
    path: str
    old_path: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    binary: bool = False
    similarity: int = 0

    @property
    def is_new(self) -> bool:
        return self.status in ('A', 'C')

    @property
    def is_deleted(self) -> bool:
        return self.status == 'D'

    @property
    def is_renamed(self) -> bool:
        return self.status == 'R'

    @property
    def is_modified(self) -> bool:
        return self.status in ('M', 'T', 'U')

def get_staged_files(cwd: Optional[str]=None) -> List[StagedFile]:
    base = ['diff', '--cached', '--no-ext-diff', '-M', '-z']
    raw = run_git(base + ['--name-status'], cwd=cwd)
    tokens = raw.split('\x00')
    files: List[StagedFile] = []
    i = 0
    while i < len(tokens):
        status = tokens[i]
        if not status:
            i += 1
            continue
        code = status[0]
        try:
            if code in 'RC':
                (old, new) = (tokens[i + 1], tokens[i + 2])
                sim = int(status[1:] or 0)
                files.append(StagedFile(code, new, old_path=old, similarity=sim))
                i += 3
            else:
                files.append(StagedFile(code, tokens[i + 1]))
                i += 2
        except IndexError:
            break
    if not files:
        return files
    stats = _parse_numstat(run_git(base + ['--numstat'], cwd=cwd))
    for f in files:
        if f.path in stats:
            (add, dele) = stats[f.path]
            if add == '-':
                f.binary = True
            else:
                (f.additions, f.deletions) = (int(add), int(dele))
    return files

def _parse_numstat(raw: str) -> Dict[str, tuple]:
    tokens = raw.split('\x00')
    out: Dict[str, tuple] = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok:
            i += 1
            continue
        parts = tok.split('\t', 2)
        if len(parts) < 3:
            i += 1
            continue
        (add, dele, rest) = parts
        if rest == '':
            if i + 2 >= len(tokens):
                break
            out[tokens[i + 2]] = (add, dele)
            i += 3
        else:
            out[rest] = (add, dele)
            i += 1
    return out

def get_added_lines(files: Sequence[StagedFile], cwd: Optional[str]=None) -> Dict[str, List[str]]:
    specs: List[str] = []
    for f in files:
        specs.append(':(literal)' + f.path)
        if f.old_path:
            specs.append(':(literal)' + f.old_path)
    if not specs:
        return {}
    raw = run_git(['-c', 'core.quotepath=off', 'diff', '--cached', '-U0', '--no-color', '--no-ext-diff', '-M', '--'] + specs, cwd=cwd)[:MAX_DIFF_CHARS]
    result: Dict[str, List[str]] = {}
    current: Optional[str] = None
    in_hunk = False
    for line in raw.splitlines():
        if line.startswith('diff --git '):
            (current, in_hunk) = (None, False)
        elif not in_hunk and line.startswith('+++ '):
            name = line[4:].split('\t')[0]
            current = name[2:] if name.startswith('b/') else None
        elif line.startswith('@@'):
            in_hunk = True
        elif in_hunk and current and line.startswith('+'):
            result.setdefault(current, []).append(line[1:])
    return result

def tracked_files(cwd: Optional[str]=None) -> List[str]:
    return [p for p in run_git(['ls-files', '-z'], cwd=cwd).split('\x00') if p]
_CLEANUP_RE = re.compile('^(|default|strip)$')

def cleanup_strips_comments(cwd: Optional[str]=None) -> bool:
    try:
        value = run_git(['config', '--get', 'commit.cleanup'], cwd=cwd).strip()
    except GitError:
        value = ''
    return bool(_CLEANUP_RE.match(value))