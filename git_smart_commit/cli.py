from __future__ import annotations
import argparse
import sys
from typing import List, Optional
from . import __version__, git, hook
from .engine import analyze

def _err(*a) -> None:
    print(*a, file=sys.stderr)

def cmd_suggest(verbose: bool) -> int:
    try:
        root = git.repo_root()
        files = git.get_staged_files(root)
    except git.GitError as e:
        _err('git-smart-commit: %s' % e)
        return 2
    if not files:
        _err('No staged files. Stage your changes first (e.g. `git add -p`).')
        return 1
    s = analyze(files, root)
    print(s.subject)
    if s.confidence == 'low':
        _err('⚠️  Low confidence: ' + s.reasons[0])
    if verbose:
        adds = sum((f.additions for f in files))
        dels = sum((f.deletions for f in files))
        _err('\n  type: %s   scope: %s   confidence: %s' % (s.type, s.scope or '-', s.confidence))
        _err('  files: %d staged (+%d -%d)' % (len(files), adds, dels))
        for f in files:
            shown = '%s -> %s' % (f.old_path, f.path) if f.old_path else f.path
            stat = 'binary' if f.binary else '+%d -%d' % (f.additions, f.deletions)
            _err('    %s  %s  %s' % (f.status, shown, stat))
        for r in s.reasons:
            _err('  why: ' + r)
    for w in s.warnings:
        _err(w)
    return 0

def _wrap(fn) -> int:
    try:
        (ok, msg) = fn()
    except git.GitError as e:
        _err('git-smart-commit: %s' % e)
        return 2
    print(msg, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='git-smart', description='Suggest Conventional Commit messages from staged changes. Fully local, zero config.')
    p.add_argument('--version', action='version', version='git-smart-commit ' + __version__)
    p.add_argument('-v', '--verbose', action='store_true', help='explain the suggestion')
    sub = p.add_subparsers(dest='command')
    sp = sub.add_parser('suggest', help='print a suggested commit message (default)')
    sp.add_argument('-v', '--verbose', action='store_true', default=argparse.SUPPRESS)
    ip = sub.add_parser('install', help='install the prepare-commit-msg hook in this repo')
    ip.add_argument('--force', action='store_true', help='replace (and back up) an existing hook')
    sub.add_parser('uninstall', help='remove the hook')
    hp = sub.add_parser('hook', help=argparse.SUPPRESS)
    hp.add_argument('msg_file')
    hp.add_argument('source', nargs='?')
    hp.add_argument('sha', nargs='?')
    return p

def main(argv: Optional[List[str]]=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    if args.command == 'hook':
        return hook.run_hook(args.msg_file, args.source)
    if args.command == 'install':
        return _wrap(lambda : hook.install(force=args.force))
    if args.command == 'uninstall':
        return _wrap(hook.uninstall)
    return cmd_suggest(args.verbose)