"""Load the shipped native sampler; the official score table remains authoritative."""
import ctypes as C
from pathlib import Path
import platform

from evaluator import get_table

ROOT = Path(__file__).resolve().parent
name = {("Windows", "AMD64"): "equity-windows-x86_64.dll",
        ("Linux", "x86_64"): "equity-linux-x86_64.so",
        ("Linux", "aarch64"): "equity-linux-aarch64.so"}.get((platform.system(), platform.machine()))
if platform.system() == "Darwin":
    name = {"arm64": "equity-macos-arm64.dylib", "x86_64": "equity-macos-x86_64.dylib"}.get(platform.machine())
LIB = None
if name and (ROOT / "native" / name).exists():
    try:
        LIB = C.CDLL(str(ROOT / "native" / name))
    except OSError:
        import warnings
        warnings.warn("Native library could not load; using slower Python equity fallback", RuntimeWarning)
if LIB is not None:
    LIB.initialize.argtypes = [C.POINTER(C.c_uint64), C.POINTER(C.c_uint32), C.c_int]
    LIB.initialize.restype = None
    LIB.evaluate.argtypes = [C.POINTER(C.c_int), C.POINTER(C.c_int), C.c_int]
    LIB.evaluate.restype = C.c_uint32
    LIB.simulate.argtypes = [C.POINTER(C.c_int), C.POINTER(C.c_int), C.c_int, C.c_int,
                             C.c_uint64, C.POINTER(C.c_double)]
    LIB.simulate.restype = None
    table = get_table()
    masks = (C.c_uint64 * len(table))(*table.keys())
    scores = (C.c_uint32 * len(table))(*table.values())
    LIB.initialize(masks, scores, len(table))
    del masks, scores


def samples(hole, board, n, seed):
    if LIB is None:
        return None
    result = (C.c_double * (n * 4))()
    LIB.simulate((C.c_int * 5)(*hole), (C.c_int * len(board))(*board), len(board), n, seed, result)
    return result


def evaluate(hole, board):
    if LIB is None:
        raise RuntimeError("Native engine unavailable")
    return LIB.evaluate((C.c_int * 5)(*hole), (C.c_int * len(board))(*board), len(board))
