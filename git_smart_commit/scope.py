from __future__ import annotations
import re
from collections import Counter
from typing import Iterable, Optional
CONTAINERS = {'packages', 'apps', 'libs', 'services', 'modules', 'plugins', 'crates'}
GENERIC = {'src', 'lib', 'app', 'source', 'internal', 'pkg', 'cmd', 'core', 'main', 'tests', 'test', '__tests__', 'spec', 'specs', 'e2e', 'docs', 'doc', 'documentation', 'styles', 'css'}

def _clean(s: str) -> Optional[str]:
    s = re.sub('[^a-z0-9_-]+', '-', s.lower()).strip('-')
    return s or None

def scope_for_path(path: str) -> Optional[str]:
    parts = path.replace('\\', '/').split('/')[:-1]
    if not parts or parts[0].startswith('.'):
        return None
    if parts[0].lower() in CONTAINERS and len(parts) > 1:
        return _clean(parts[1])
    while parts and parts[0].lower() in GENERIC:
        parts = parts[1:]
    return _clean(parts[0]) if parts else None

def derive_scope(paths: Iterable[str]) -> Optional[str]:
    paths = list(paths)
    counts = Counter((s for s in map(scope_for_path, paths) if s))
    if not counts:
        return None
    (scope, n) = counts.most_common(1)[0]
    return scope if n * 2 > len(paths) else None