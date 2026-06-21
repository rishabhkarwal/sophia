"""
promote a texel-tuned eval candidate into sophia/engine/core/parameters.py
by using the _apply_tune_params mechanism and writing the module back

usage:
    venv/bin/python tune/promote_eval_candidate.py tune/output/candidates/<candidate>.json [--dry-run]
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'sophia'))

PARAMETERS_PY = ROOT / 'sophia' / 'engine' / 'core' / 'parameters.py'


def apply_and_dump(candidate_path, dry_run=False):
    """load the candidate, apply it via SOPHIA_TUNE_PARAMS, then re-read all
    relevant globals and write them back to the parameters.py source
    """
    import re

    os.environ['SOPHIA_TUNE_PARAMS'] = str(Path(candidate_path).resolve())
    import importlib
    import engine.core.parameters as p
    importlib.reload(p)

    src = PARAMETERS_PY.read_text()
    lines = src.splitlines(keepends=True)
    changed = []

    # scalar int/float replacements
    SCALAR_NAMES = [
        'DOUBLED_PAWN_PENALTY', 'ISOLATED_PAWN_PENALTY',
        'KNIGHT_OUTPOST_BONUS', 'ROOK_ON_SEVENTH_RANK',
        'ROOK_BEHIND_PASSED_PAWN', 'ROOK_BATTERY_BONUS',
        'QUEEN_ROOK_BATTERY_BONUS', 'ROOK_OPEN_FILE', 'ROOK_SEMI_OPEN_FILE',
        'BISHOP_PAIR_BONUS', 'TRAPPED_PIECE_PENALTY',
        'KNIGHT_MOBILITY', 'BISHOP_MOBILITY', 'ROOK_MOBILITY', 'QUEEN_MOBILITY',
        'KING_PAWN_SHIELD_BONUS', 'KING_TO_CENTRE_BONUS', 'KING_TO_ENEMY_PAWNS_BONUS',
        'TRADE_BONUS_PER_PIECE', 'TRADE_PENALTY_PER_PIECE',
        'WINNING_THRESHOLD', 'LOSING_THRESHOLD',
        'MOP_UP_ACTIVATION', 'MOP_UP_CENTRE_WEIGHT', 'MOP_UP_DISTANCE_WEIGHT',
    ]
    FLOAT_NAMES = [
        'PHASE_GATE_DOUBLED_PAWNS', 'PHASE_GATE_KING_SAFETY',
        'PHASE_GATE_MOBILITY', 'PHASE_GATE_KING_ENDGAME',
        'DIAGONAL_BATTERY_SCALE',
    ]

    for i, line in enumerate(lines):
        for name in SCALAR_NAMES + FLOAT_NAMES:
            m = re.match(rf'^({re.escape(name)}\s*=\s*)([\d\.\-]+)(.*)', line)
            if m:
                new_val = getattr(p, name)
                if isinstance(new_val, float):
                    new_val_str = f'{new_val:.4f}'
                else:
                    new_val_str = str(new_val)
                comment = m.group(3).rstrip('\n')
                new_line = f'{m.group(1)}{new_val_str}{comment}\n'
                if new_line != line:
                    changed.append(f'  {name}: {m.group(2)} -> {new_val_str}')
                lines[i] = new_line
                break

    # MG_VALUES and EG_VALUES dict entries
    from engine.core.constants import PAWN, KNIGHT, BISHOP, ROOK, QUEEN
    piece_map = {PAWN: 'PAWN', KNIGHT: 'KNIGHT', BISHOP: 'BISHOP',
                 ROOK: 'ROOK', QUEEN: 'QUEEN'}
    in_mg = False
    in_eg = False
    for i, line in enumerate(lines):
        if 'MG_VALUES' in line and '=' in line:
            in_mg = True; in_eg = False
        elif 'EG_VALUES' in line and '=' in line:
            in_eg = True; in_mg = False
        elif in_mg or in_eg:
            for enc, name in piece_map.items():
                m = re.match(rf'^(\s+{enc}:\s*)(\d+)(,.*)', line)
                if m:
                    val = p.MG_VALUES[enc] if in_mg else p.EG_VALUES[enc]
                    new_line = f'{m.group(1)}{val}{m.group(3)}\n'
                    if new_line != line:
                        dict_name = 'MG_VALUES' if in_mg else 'EG_VALUES'
                        changed.append(f'  {dict_name}[{enc}]({name}): {m.group(2)} -> {val}')
                    lines[i] = new_line
                    break
            if '}' in line:
                in_mg = in_eg = False

    # PASSED_PAWN_BONUS list
    for i, line in enumerate(lines):
        if re.match(r'^PASSED_PAWN_BONUS\s*=', line):
            new_vals = ', '.join(str(v) for v in p.PASSED_PAWN_BONUS)
            j = i
            while j < len(lines) and ']' not in lines[j]:
                j += 1
            old = ''.join(lines[i:j+1]).strip()
            new_line = f'PASSED_PAWN_BONUS = [{new_vals}]\n'
            if new_line.strip() != old:
                changed.append(f'  PASSED_PAWN_BONUS: updated')
            lines[i:j+1] = [new_line]
            break

    # PSQT list assignments
    PSQT_NAMES = [
        'mg_pawn', 'eg_pawn', 'mg_knight', 'eg_knight',
        'mg_bishop', 'eg_bishop', 'mg_rook', 'eg_rook',
        'mg_queen', 'eg_queen', 'mg_king', 'eg_king',
    ]
    for psqt_lower in PSQT_NAMES:
        psqt_upper = psqt_lower.upper()
        for i, line in enumerate(lines):
            if re.match(rf'^{psqt_upper}\s*=\s*\[', line):
                j = i
                while j < len(lines) and ']' not in lines[j]:
                    j += 1
                new_arr = getattr(p, psqt_upper)
                new_line = f'{psqt_upper} = [{", ".join(str(v) for v in new_arr)}]\n'
                old_line = ''.join(lines[i:j+1]).strip()
                if new_line.strip() != old_line:
                    changed.append(f'  {psqt_upper}: updated')
                lines[i:j+1] = [new_line]
                break

    print(f'{len(changed)} parameters changed:')
    for c in changed[:20]:
        print(c)
    if len(changed) > 20:
        print(f'  ... and {len(changed)-20} more (PSQT entries)')

    new_src = ''.join(lines)
    if not dry_run:
        PARAMETERS_PY.write_text(new_src)
        print(f'\nwritten: {PARAMETERS_PY}')
    else:
        print('\n[dry-run] no files written')

    return changed


def rebuild_cython():
    print('\nrebuilding Cython extensions...')
    result = subprocess.run(
        ['../venv/bin/python', 'setup.py', 'build_ext', '--inplace'],
        cwd=ROOT / 'sophia',
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print('build failed:')
        print(result.stderr[-3000:])
        sys.exit(1)
    print('build succeeded')


def main():
    dry_run = '--dry-run' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print('usage: promote_eval_candidate.py <candidate.json> [--dry-run]')
        sys.exit(1)

    candidate_path = args[0]
    print(f'candidate: {candidate_path}')
    print(f'mode: {"dry-run" if dry_run else "live write"}\n')

    changed = apply_and_dump(candidate_path, dry_run)

    if not dry_run and changed:
        rebuild_cython()

    print('\ndone.')


if __name__ == '__main__':
    main()
