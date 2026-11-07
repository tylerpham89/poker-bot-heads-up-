"""Create the portable submission and compare archived runtime bytes to source."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
RUNTIME=['agent.py','strategy.py','fallback_strategy.py','native_engine.py',
         'preflop.py','preflop-model.json','game.py','evaluator.py','requirements.txt']
EXCLUDE={'starter','archive-v1','__pycache__','.pytest_cache','.git','.venv','.packaging-check','.zig-cache'}
EXCLUDE_SUFFIX={'.zip','.log','.pyc','.pdb','.lib','.npz'}


def main():
    binaries=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'native').iterdir()
                    if p.suffix in {'.dll','.so','.dylib'})
    required=RUNTIME+binaries
    if len(binaries)!=5:
        raise RuntimeError('Expected all five supported native libraries')
    manifest={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in required}
    (ROOT/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    files=sorted(p for p in ROOT.rglob('*') if p.is_file()
                 and not (set(p.relative_to(ROOT).parts)&EXCLUDE)
                 and p.suffix not in EXCLUDE_SUFFIX)
    target=ROOT/'pocketedge-submission.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Archive integrity failure')
        for name,digest in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest:
                raise RuntimeError(f'Archive mismatch: {name}')
        for name in ('RUN_WITH_FRIEND.md','OPTIMIZATION.md','judge_engine.py',
                     'requirements-dev.txt','test_agent.py','test_strategy.py','test_native.py'):
            if name not in archive.namelist():
                raise RuntimeError(f'Missing {name}')
    print(f'Packaged {len(files)} files, {target.stat().st_size:,} bytes; runtime hashes verified.')


if __name__=='__main__':
    main()
