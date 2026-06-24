#!/bin/bash
cd "$(dirname "$0")"

PYTHON=${PYTHON:-../venv/bin/python}

if [ ! -x "$PYTHON" ]; then
    echo "Python interpreter not found: $PYTHON" >&2
    exit 1
fi

# auto-recompile cython extensions if any .so is missing
needs_build=0
while IFS= read -r pyx_file; do
    module_path="${pyx_file%.pyx}"
    if ! ls "${module_path}".cpython-*.so &>/dev/null; then
        needs_build=1
        break
    fi
done < <(find engine -name '*.pyx' -print)

if [ "$needs_build" -eq 1 ]; then
    echo "cython extensions not found, building..." >&2
    "$PYTHON" setup.py build_ext --inplace --quiet 2>&1 | tail -3 >&2
fi

"$PYTHON" -u main.py
