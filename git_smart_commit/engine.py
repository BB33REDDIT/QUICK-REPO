import posixpath
from typing import List, Optional
from collections import namedtuple

AnalysisResult = namedtuple('AnalysisResult', ['subject'])

def is_lockfile(path: str) -> bool:
    return path.lower().endswith(('package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'pipfile.lock', 'poetry.lock'))

def _verb(fs: List) -> str:
    if all(getattr(f, 'is_deleted', False) for f in fs):
        return 'remove'
    if all(getattr(f, 'is_added', False) for f in fs):
        return 'add'
    return 'update'

def _subject_of(fs: List, category: str, scope: Optional[str]) -> str:
    if len(fs) == 1:
        return posixpath.splitext(posixpath.basename(fs[0].path))[0]
    if category == 'deps':
        return 'dependencies'
    
    dirs = {posixpath.dirname(f.path) for f in fs}
    if len(dirs) == 1:
        d = dirs.pop()
        return d if d else 'core'
    return 'multiple files'

def _determine_category(fs: List) -> str:
    if any(is_lockfile(f.path) for f in fs): return 'deps'
    if any('.github' in f.path.lower() for f in fs): return 'ci'
    if any('docker' in f.path.lower() for f in fs): return 'build'
    if any('test' in f.path.lower() for f in fs): return 'test'
    if any(f.path.lower().endswith(('.md', '.txt')) for f in fs): return 'docs'
    if any(f.path.lower().endswith(('.css', '.scss', '.less')) for f in fs): return 'style'
    return 'core'

def _describe(ctype: str, category: str, fs: List, scope: Optional[str]) -> str:
    if category == 'deps':
        return 'update lockfile' if all(is_lockfile(f.path) for f in fs) else 'update dependencies'
    if category == 'ci':
        return 'update CI workflow'
    if category == 'build':
        docker = any(posixpath.basename(f.path).lower().startswith(('dockerfile', 'docker-compose')) or f.path.lower().endswith('.dockerfile') for f in fs)
        return 'update Docker setup' if docker else 'update build configuration'
    
    what = _subject_of(fs, category, scope)
    verb = _verb(fs)
    
    if category == 'test':
        return 'add tests for %s' % what if verb == 'add' else 'update tests for %s' % what
    if category == 'style':
        return '%s styles for %s' % (verb, what)
    if category == 'docs':
        return 'update documentation' if len(fs) > 2 else '%s %s docs' % (verb, what)
        
    if ctype == 'refactor':
        if all(getattr(f, 'is_renamed', False) for f in fs) and len(fs) == 1:
            old_name = getattr(fs[0], 'old_path', '')
            old = posixpath.splitext(posixpath.basename(old_name))[0] if old_name else 'file'
            new = posixpath.splitext(posixpath.basename(fs[0].path))[0]
            return 'rename %s to %s' % (old, new) if old != new else 'move %s' % new
        if all(getattr(f, 'is_deleted', False) for f in fs):
            return 'remove %s' % what
        return 'restructure %s' % what  
        
    return '%s %s' % (verb, what)

def analyze(git_files: List, root: str) -> Optional[AnalysisResult]:
    if not git_files:
        return None
        
    category = _determine_category(git_files)
    
    ctype = 'chore'
    if category in ('docs', 'test', 'ci', 'build'):
        ctype = category
    elif category == 'style':
        ctype = 'style'
    elif any(f.path.endswith('.py') for f in git_files):
        ctype = 'fix' 
        
    scope = None 
    
    description = _describe(ctype, category, git_files, scope)
    return AnalysisResult(subject=f"{ctype}: {description}")