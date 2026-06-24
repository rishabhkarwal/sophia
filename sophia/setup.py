from setuptools import setup, Extension
from Cython.Build import cythonize

# -O3 -march=native: full optimisation + use host CPU instructions (AVX2/BMI2
# for popcnt/tzcnt if available). -ffast-math: allow FP reassociation (safe
# here as only use integers in search; float only for timing).
EXTRA_COMPILE = ["-O3", "-march=native", "-ffast-math"]
EXTRA_LINK    = []

# build order matters for .pxd resolution: bits and state must come before
# anything that cimports them. cython resolves .pxd at compile time, so the
# order here only affects incremental builds — a clean build is always safe.
PYX_FILES = [
    "engine/core/bits.pyx",
    "engine/core/move.pyx",
    "engine/core/zobrist.pyx",
    "engine/board/state.pyx",
    "engine/board/move_exec.pyx",
    "engine/moves/precomputed.pyx",
    "engine/moves/legality.pyx",
    "engine/moves/generator.pyx",
    "engine/uci/perft.pyx",
    "engine/search/transposition.pyx",
    "engine/search/see.pyx",
    "engine/search/evaluation.pyx",
    "engine/search/ordering.pyx",
    "engine/search/search.pyx",
]

extensions = cythonize(
    PYX_FILES,
    compiler_directives={
        "language_level":   "3",
        "annotation_typing": False,
        "boundscheck":       False,
        "wraparound":        False,
        "cdivision":        True,
    },
    include_path=["."], # so cython can find .pxd files in subdirs
)

# inject compiler flags into every extension
for ext in extensions:
    ext.extra_compile_args = EXTRA_COMPILE
    ext.extra_link_args    = EXTRA_LINK

setup(ext_modules=extensions)
