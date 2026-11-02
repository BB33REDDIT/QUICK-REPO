from __future__ import annotations
import posixpath
from typing import Iterable, List, Optional, Set
from .git import StagedFile
from .rules import categorize, DOC_STEMS
from .scope import scope_for_path
WARNING = '⚠️ Warning: Staged files span multiple unrelated areas. Consider splitting this commit.'
THRESHOLD = 3

def area_of(path: str) -> Optional[str]:
    cat = categorize(path)
    if cat in ('source', 'test', 'style'):
        return 'code:%s' % (scope_for_path(path) or '(root)')
    if cat == 'docs':
        return None if '/' not in path else 'docs'
    if cat in ('ci', 'build'):
        return 'infra'
    return cat

def find_areas(files: Iterable[StagedFile]) -> List[str]:
    seen: Set[str] = set()
    for f in files:
        a = area_of(f.path)
        if a:
            seen.add(a)
    return sorted(seen)

def check_split(files: Iterable[StagedFile]) -> Optional[List[str]]:
    areas = find_areas(files)
    return areas if len(areas) >= THRESHOLD else None