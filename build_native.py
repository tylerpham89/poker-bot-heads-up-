"""Rebuild shipped libraries using Zig 0.13.0 (development only).

python -m pip install ziglang==0.13.0
python build_native.py
No compiler is needed to run the packaged bot.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
TARGETS=[('x86_64-windows-gnu','equity-windows-x86_64.dll'),
         ('x86_64-linux-musl','equity-linux-x86_64.so'),
         ('aarch64-linux-musl','equity-linux-aarch64.so'),
         ('aarch64-macos','equity-macos-arm64.dylib'),
         ('x86_64-macos','equity-macos-x86_64.dylib')]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--zig')
    args=parser.parse_args()
    zig=args.zig or shutil.which('zig')
    if not zig:
        import ziglang
        zig=str(Path(ziglang.__file__).parent/('zig.exe' if os.name=='nt' else 'zig'))
    env=dict(os.environ)
    env.setdefault('ZIG_GLOBAL_CACHE_DIR',str(ROOT.parent/'.zig-cache'/'global'))
    env.setdefault('ZIG_LOCAL_CACHE_DIR',str(ROOT.parent/'.zig-cache'/'local'))
    for target,name in TARGETS:
        flags=['-O3','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-shared']
        if 'windows' in target:
            flags.append('-mno-stack-arg-probe')
        subprocess.run([zig,'cc',*flags,'-target',target,'native/equity.c','-o',f'native/{name}'],
                       check=True,cwd=ROOT,env=env)
        print(f'Built {name}',flush=True)


if __name__=='__main__':
    main()
