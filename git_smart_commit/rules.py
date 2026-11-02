from __future__ import annotations
import posixpath
import re
from typing import Iterable, List, Optional, Set, Tuple
from .git import StagedFile
TEST_DIRS = {'tests', 'test', '__tests__', 'spec', 'specs', 'e2e'}
DOC_DIRS = {'docs', 'doc', 'documentation'}
DOC_STEMS = {'readme', 'changelog', 'license', 'contributing', 'authors', 'notice', 'copying'}
DEPS_NAMES = {'package.json', 'package-lock.json', 'npm-shrinkwrap.json', 'yarn.lock', 'pnpm-lock.yaml', 'bun.lock', 'bun.lockb', 'pipfile', 'pipfile.lock', 'poetry.lock', 'uv.lock', 'pdm.lock', 'go.mod', 'go.sum', 'cargo.toml', 'cargo.lock', 'gemfile', 'gemfile.lock', 'composer.json', 'composer.lock', 'constraints.txt'}
LOCKFILES = {'package-lock.json', 'npm-shrinkwrap.json', 'yarn.lock', 'pnpm-lock.yaml', 'bun.lock', 'bun.lockb', 'pipfile.lock', 'poetry.lock', 'uv.lock', 'pdm.lock', 'go.sum', 'cargo.lock', 'gemfile.lock', 'composer.lock'}
CI_NAMES = {'.gitlab-ci.yml', '.travis.yml', 'jenkinsfile', 'azure-pipelines.yml', 'bitbucket-pipelines.yml', '.drone.yml', 'appveyor.yml'}
STYLE_EXTS = {'.css', '.scss', '.sass', '.less', '.styl', '.pcss'}
SOURCE_EXTS = {'.py', '.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.go', '.rs', '.java', '.kt', '.rb', '.php', '.c', '.h', '.cc', '.cpp', '.hpp', '.cs', '.swift', '.scala', '.vue', '.svelte', '.dart', '.lua', '.sh', '.sql', '.ex', '.exs'}
CONFIG_EXTS = {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env'}
_REQ_RE = re.compile('^requirements[\\w.\\-]*\\.txt$')
_COMPOSE_RE = re.compile('^docker-compose[\\w.\\-]*\\.ya?ml$|^compose\\.ya?ml$')
_BUILD_CFG_RE = re.compile('^(webpack|vite|rollup|esbuild|rspack|tsup|babel)\\.config\\.\\w+$')
_TAILWIND_RE = re.compile('^(tailwind|postcss)\\.config\\.\\w+$')
_TEST_NAME_RE = re.compile('\\.(test|spec)\\.|^test_.+\\.py$|_test\\.(py|go|rb|rs|exs)$|_spec\\.rb$')
_FIX_RE = re.compile('\\b(fix(e[sd])?|bug(fix)?|hotfix|crash(es|ed)?|regression|workaround|typo)\\b', re.I)
TYPE_FOR_CATEGORY = {'deps': 'chore', 'test': 'test', 'style': 'style', 'docs': 'docs', 'ci': 'ci', 'build': 'build', 'config': 'chore', 'other': 'chore'}
CATEGORY_PRIORITY = ['ci', 'build', 'test', 'style', 'docs', 'deps', 'config', 'other']

def categorize(path: str) -> str:
    p = path.replace('\\', '/').lower()
    name = posixpath.basename(p)
    parts = p.split('/')[:-1]
    (stem, ext) = posixpath.splitext(name)
    if '/.github/workflows/' in '/' + p or '.circleci' in parts or name in CI_NAMES:
        return 'ci'
    if name in DEPS_NAMES or _REQ_RE.match(name):
        return 'deps'
    if name.startswith('dockerfile') or name.endswith('.dockerfile') or name in {'.dockerignore', 'makefile', 'cmakelists.txt'} or _COMPOSE_RE.match(name) or _BUILD_CFG_RE.match(name):
        return 'build'
    if TEST_DIRS.intersection(parts) or _TEST_NAME_RE.search(name):
        return 'test'
    if ext in STYLE_EXTS or _TAILWIND_RE.match(name):
        return 'style'
    if parts and parts[0] in DOC_DIRS or ext in {'.md', '.mdx', '.rst', '.adoc'} or stem in DOC_STEMS:
        return 'docs'
    if '.config.' in name:
        return 'config'
    if ext in SOURCE_EXTS:
        return 'source'
    if ext in CONFIG_EXTS or name.startswith('.'):
        return 'config'
    return 'other'

def is_lockfile(path: str) -> bool:
    return posixpath.basename(path).lower() in LOCKFILES

def _norm(s: str) -> str:
    return re.sub('[^a-z0-9]', '', s.lower())

def strip_test_affixes(stem: str) -> str:
    s = re.sub('\\.(test|spec)$', '', stem, flags=re.I)
    s = re.sub('(?<=[a-z0-9])(Tests?|Spec)$', '', s)
    s = re.sub('^test[_-]', '', s, flags=re.I)
    s = re.sub('[_-](tests?|spec)$', '', s, flags=re.I)
    return s

def test_target(path: str) -> str:
    stem = posixpath.splitext(posixpath.basename(path))[0]
    return _norm(strip_test_affixes(stem))

def source_key(path: str) -> str:
    return _norm(posixpath.splitext(posixpath.basename(path))[0])
_TRIVIAL_SOURCES = {'__init__.py', 'conftest.py', 'setup.py'}

def decide_source_type(src: List[StagedFile], added_lines, tracked_test_targets) -> Tuple[str, str, List[str]]:
    new = [f for f in src if f.is_new and posixpath.basename(f.path) not in _TRIVIAL_SOURCES]
    if new:
        targets = tracked_test_targets()
        unmatched = [f for f in new if source_key(f.path) not in targets]
        if unmatched:
            names = ', '.join((f.path for f in unmatched[:3]))
            more = ' …' if len(unmatched) > 3 else ''
            return ('feat', 'low', ['New source file without a matching test: %s%s' % (names, more)])
        return ('feat', 'high', ['New source file(s) with matching test(s)'])
    if any((f.is_new for f in src)):
        return ('feat', 'medium', ['New package/module scaffolding'])
    candidates = [f for f in src if f.is_modified or (f.is_renamed and f.similarity < 100)]
    lines = added_lines(candidates) if candidates else {}
    hits = [f for f in candidates if any((_FIX_RE.search(l) for l in lines.get(f.path, ())))]
    if hits:
        return ('fix', 'medium', ['Added lines mention a fix/bug keyword in %s' % hits[0].path])
    if any((f.is_renamed or f.is_deleted for f in src)):
        what = 'renamed' if any((f.is_renamed for f in src)) else 'deleted'
        return ('refactor', 'medium', ['Source file(s) %s without new functionality' % what])
    adds = sum((f.additions for f in src))
    dels = sum((f.deletions for f in src))
    if dels > adds:
        return ('refactor', 'medium', ['Modified source with more deletions (-%d) than additions (+%d)' % (dels, adds)])
    return ('feat', 'low', ['Modified source with no fix/refactor signal; guessing feat'])