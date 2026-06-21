"""
texel tuner for the Cython sophia engine

minimises: MSE = mean((sigmoid(white_eval / K) - label)^2)
  label = SF WDL expected score (from annotate_fens.py), in [0, 1]

runs under the project CPython venv because the engine modules are Cython extensions:
    venv/bin/python tune/texel_tune.py [fens_file] [max_positions] [max_passes]

results are written to tune/best_params_cython_wdl.json and
tune/best_parameters_cython_wdl.py whenever MSE improves
"""

import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'sophia'))

from engine.board.fen_parser import load_from_fen
from engine.core.constants import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
import engine.core.parameters as _params
import engine.search.evaluation as _eval
from engine.moves.legality import is_in_check
from engine.search.evaluation import evaluate

WDL_PARAMS_OUT = os.path.join('tune', 'best_params_cython_wdl.json')
WDL_PARAMETERS_OUT = os.path.join('tune', 'best_parameters_cython_wdl.py')
_OUTPUT_PARAMS_PATH = WDL_PARAMS_OUT
_OUTPUT_PARAMETERS_PATH = WDL_PARAMETERS_OUT


# scalar eval params: (name, default, low, high)
SCALAR_PARAMS = [
    ('mg_pawn',   _params.MG_VALUES[PAWN],   60, 120),
    ('mg_knight', _params.MG_VALUES[KNIGHT], 250, 420),
    ('mg_bishop', _params.MG_VALUES[BISHOP], 270, 450),
    ('mg_rook',   _params.MG_VALUES[ROOK],   380, 580),
    ('mg_queen',  _params.MG_VALUES[QUEEN],  880, 1150),
    ('eg_pawn',   _params.EG_VALUES[PAWN],   60, 130),
    ('eg_knight', _params.EG_VALUES[KNIGHT], 200, 370),
    ('eg_bishop', _params.EG_VALUES[BISHOP], 210, 380),
    ('eg_rook',   _params.EG_VALUES[ROOK],   400, 620),
    ('eg_queen',  _params.EG_VALUES[QUEEN],  800, 1080),
    ('doubled_pawn_penalty',   _params.DOUBLED_PAWN_PENALTY,  0, 40),
    ('isolated_pawn_penalty',  _params.ISOLATED_PAWN_PENALTY, 0, 40),
    ('passed_pawn_rank2',      _params.PASSED_PAWN_BONUS[1],  0, 30),
    ('passed_pawn_rank3',      _params.PASSED_PAWN_BONUS[2],  0, 40),
    ('passed_pawn_rank4',      _params.PASSED_PAWN_BONUS[3],  0, 60),
    ('passed_pawn_rank5',      _params.PASSED_PAWN_BONUS[4], 20, 140),
    ('passed_pawn_rank6',      _params.PASSED_PAWN_BONUS[5], 60, 280),
    ('passed_pawn_rank7',      _params.PASSED_PAWN_BONUS[6], 100, 400),
    ('knight_outpost_bonus',   _params.KNIGHT_OUTPOST_BONUS,  0, 40),
    ('rook_on_seventh_rank',   _params.ROOK_ON_SEVENTH_RANK,  0, 30),
    ('rook_behind_passed_pawn', _params.ROOK_BEHIND_PASSED_PAWN, 0, 25),
    ('rook_battery_bonus',     _params.ROOK_BATTERY_BONUS, 0, 30),
    ('queen_rook_battery_bonus', _params.QUEEN_ROOK_BATTERY_BONUS, 0, 30),
    ('rook_open_file',         _params.ROOK_OPEN_FILE, 5, 35),
    ('rook_semi_open_file',    _params.ROOK_SEMI_OPEN_FILE, 0, 20),
    ('bishop_pair_bonus',      _params.BISHOP_PAIR_BONUS, 5, 50),
    ('trapped_piece_penalty',  _params.TRAPPED_PIECE_PENALTY, 0, 100),
    ('knight_mobility',        _params.KNIGHT_MOBILITY, 0, 8),
    ('bishop_mobility',        _params.BISHOP_MOBILITY, 0, 8),
    ('rook_mobility',          _params.ROOK_MOBILITY, 0, 10),
    ('queen_mobility',         _params.QUEEN_MOBILITY, 0, 6),
    ('king_pawn_shield_bonus', _params.KING_PAWN_SHIELD_BONUS, 0, 20),
    ('king_to_centre_bonus',       _params.KING_TO_CENTRE_BONUS, 0, 40),
    ('king_to_enemy_pawns_bonus',  _params.KING_TO_ENEMY_PAWNS_BONUS, 0, 40),
    ('trade_bonus_per_piece',   _params.TRADE_BONUS_PER_PIECE, 0, 50),
    ('trade_penalty_per_piece', _params.TRADE_PENALTY_PER_PIECE, 0, 60),
    ('winning_threshold',       _params.WINNING_THRESHOLD, 100, 400),
    ('losing_threshold',        _params.LOSING_THRESHOLD, -300, -50),
    ('mop_up_activation',       _params.MOP_UP_ACTIVATION, 100, 400),
    ('mop_up_centre_weight',    _params.MOP_UP_CENTRE_WEIGHT, 0, 12),
    ('mop_up_distance_weight',  _params.MOP_UP_DISTANCE_WEIGHT, 0, 8),
]

# float params: (name, default, low, high)
FLOAT_PARAMS = [
    ('phase_gate_doubled_pawns', _params.PHASE_GATE_DOUBLED_PAWNS, 0.5, 1.0),
    ('phase_gate_king_safety',   _params.PHASE_GATE_KING_SAFETY,   0.3, 0.9),
    ('phase_gate_mobility',      _params.PHASE_GATE_MOBILITY,      0.2, 0.8),
    ('phase_gate_king_endgame',  _params.PHASE_GATE_KING_ENDGAME,  0.2, 0.6),
    ('diagonal_battery_scale',   _params.DIAGONAL_BATTERY_SCALE,   0.0, 1.0),
]

PSQT_NAMES = ['mg_pawn', 'eg_pawn', 'mg_knight', 'eg_knight',
              'mg_bishop', 'eg_bishop', 'mg_rook', 'eg_rook',
              'mg_queen', 'eg_queen', 'mg_king', 'eg_king']

PSQT_DELTA = 30

SCALAR_TO_CONST = {
    'doubled_pawn_penalty':    'DOUBLED_PAWN_PENALTY',
    'isolated_pawn_penalty':   'ISOLATED_PAWN_PENALTY',
    'knight_outpost_bonus':    'KNIGHT_OUTPOST_BONUS',
    'rook_on_seventh_rank':    'ROOK_ON_SEVENTH_RANK',
    'rook_behind_passed_pawn': 'ROOK_BEHIND_PASSED_PAWN',
    'rook_battery_bonus':      'ROOK_BATTERY_BONUS',
    'queen_rook_battery_bonus':'QUEEN_ROOK_BATTERY_BONUS',
    'rook_open_file':          'ROOK_OPEN_FILE',
    'rook_semi_open_file':     'ROOK_SEMI_OPEN_FILE',
    'bishop_pair_bonus':       'BISHOP_PAIR_BONUS',
    'trapped_piece_penalty':   'TRAPPED_PIECE_PENALTY',
    'knight_mobility':         'KNIGHT_MOBILITY',
    'bishop_mobility':         'BISHOP_MOBILITY',
    'rook_mobility':           'ROOK_MOBILITY',
    'queen_mobility':          'QUEEN_MOBILITY',
    'king_pawn_shield_bonus':  'KING_PAWN_SHIELD_BONUS',
    'king_to_centre_bonus':    'KING_TO_CENTRE_BONUS',
    'king_to_enemy_pawns_bonus':'KING_TO_ENEMY_PAWNS_BONUS',
    'trade_bonus_per_piece':   'TRADE_BONUS_PER_PIECE',
    'trade_penalty_per_piece': 'TRADE_PENALTY_PER_PIECE',
    'winning_threshold':       'WINNING_THRESHOLD',
    'losing_threshold':        'LOSING_THRESHOLD',
    'mop_up_activation':       'MOP_UP_ACTIVATION',
    'mop_up_centre_weight':    'MOP_UP_CENTRE_WEIGHT',
    'mop_up_distance_weight':  'MOP_UP_DISTANCE_WEIGHT',
}

FLOAT_TO_CONST = {
    'phase_gate_doubled_pawns': 'PHASE_GATE_DOUBLED_PAWNS',
    'phase_gate_king_safety':   'PHASE_GATE_KING_SAFETY',
    'phase_gate_mobility':      'PHASE_GATE_MOBILITY',
    'phase_gate_king_endgame':  'PHASE_GATE_KING_ENDGAME',
    'diagonal_battery_scale':   'DIAGONAL_BATTERY_SCALE',
}


def apply_scalars(scalars, floats):
    for param_name, const_name in SCALAR_TO_CONST.items():
        value = scalars[param_name]
        setattr(_params, const_name, value)
        setattr(_eval, const_name, value)
    for param_name, const_name in FLOAT_TO_CONST.items():
        value = floats[param_name]
        setattr(_params, const_name, value)
        setattr(_eval, const_name, value)

    passed = [0, scalars['passed_pawn_rank2'], scalars['passed_pawn_rank3'],
              scalars['passed_pawn_rank4'], scalars['passed_pawn_rank5'],
              scalars['passed_pawn_rank6'], scalars['passed_pawn_rank7'], 0]
    _params.PASSED_PAWN_BONUS[:] = passed
    _eval.PASSED_PAWN_BONUS = _params.PASSED_PAWN_BONUS

    _params.MG_VALUES.clear()
    _params.MG_VALUES.update({
        PAWN: scalars['mg_pawn'], KNIGHT: scalars['mg_knight'],
        BISHOP: scalars['mg_bishop'], ROOK: scalars['mg_rook'],
        QUEEN: scalars['mg_queen'], KING: 0,
    })
    _params.EG_VALUES.clear()
    _params.EG_VALUES.update({
        PAWN: scalars['eg_pawn'], KNIGHT: scalars['eg_knight'],
        BISHOP: scalars['eg_bishop'], ROOK: scalars['eg_rook'],
        QUEEN: scalars['eg_queen'], KING: 0,
    })
    _eval.MG_VALUES = _params.MG_VALUES
    _eval.EG_VALUES = _params.EG_VALUES


def apply_psqt(psqt):
    for name in PSQT_NAMES:
        getattr(_params, name.upper())[:] = psqt[name]
    _eval.PSQTs = _params.PSQTs


def apply_all(scalars, floats, psqt):
    apply_scalars(scalars, floats)
    apply_psqt(psqt)
    _eval.init_eval_tables()


def load_dataset(path, cap):
    raw = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fen, label = line.rsplit(' | ', 1)
            raw.append((fen, float(label)))

    # drop in-check positions (static eval can't model the check)
    kept = []
    dropped_check = 0
    for fen, label in raw:
        state = load_from_fen(fen)
        if is_in_check(state, state.is_white):
            dropped_check += 1
            continue
        kept.append((fen, label))

    if cap and len(kept) > cap:
        # deterministic stride sample — spreads across the whole file
        stride = len(kept) / cap
        kept = [kept[int(i * stride)] for i in range(cap)]

    print(f'loaded {len(raw)} positions, dropped {dropped_check} in-check, '
          f'using {len(kept)}', flush=True)
    return kept


def make_eval_fn():
    def white_eval(fen):
        state = load_from_fen(fen)
        score = evaluate(state)
        return score if state.is_white else -score

    return white_eval


def mse(positions, white_eval, K):
    total = 0.0
    inv_k = 1.0 / K
    for fen, label in positions:
        s = white_eval(fen)
        sig = 1.0 / (1.0 + math.exp(-s * inv_k))
        d = sig - label
        total += d * d
    return total / len(positions)


def fit_k(positions, white_eval):
    # cache raw white evals once (params are fixed during K fit), then scan K
    evals = [(white_eval(fen), label) for fen, label in positions]

    def mse_for_k(K):
        inv_k = 1.0 / K
        total = 0.0
        for s, label in evals:
            sig = 1.0 / (1.0 + math.exp(-s * inv_k))
            d = sig - label
            total += d * d
        return total / len(evals)

    # ternary search over K in [50, 800]
    lo, hi = 50.0, 800.0
    for _ in range(40):
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        if mse_for_k(m1) < mse_for_k(m2):
            hi = m2
        else:
            lo = m1
    K = (lo + hi) / 2
    return K, mse_for_k(K)


def configure_outputs(params_path, parameters_path):
    global _OUTPUT_PARAMS_PATH, _OUTPUT_PARAMETERS_PATH
    _OUTPUT_PARAMS_PATH = params_path
    _OUTPUT_PARAMETERS_PATH = parameters_path


def _format_list(name, values):
    lines = [f'{name} = [\n']
    for r in range(8):
        row = values[r * 8:(r + 1) * 8]
        lines.append('    ' + ', '.join(f'{v:4d}' for v in row) + ',\n')
    lines.append(']\n\n')
    return lines


def save_best(scalars, floats, psqt, K, mse_val):
    os.makedirs(os.path.dirname(_OUTPUT_PARAMS_PATH) or '.', exist_ok=True)
    os.makedirs(os.path.dirname(_OUTPUT_PARAMETERS_PATH) or '.', exist_ok=True)
    with open(_OUTPUT_PARAMS_PATH, 'w') as f:
        json.dump({
            'mse': mse_val,
            'K': K,
            'params': scalars,
            'phase_thresholds': floats,
            'psqt': psqt,
        }, f, indent=2)

    lines = ['"""Tuned parameter overrides generated by texel_tune.py"""\n\n']
    lines.append('from engine.core.constants import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING\n\n')
    lines.append(f'MG_VALUES = {{PAWN: {scalars["mg_pawn"]}, KNIGHT: {scalars["mg_knight"]}, ')
    lines.append(f'BISHOP: {scalars["mg_bishop"]}, ROOK: {scalars["mg_rook"]}, ')
    lines.append(f'QUEEN: {scalars["mg_queen"]}, KING: 0}}\n')
    lines.append(f'EG_VALUES = {{PAWN: {scalars["eg_pawn"]}, KNIGHT: {scalars["eg_knight"]}, ')
    lines.append(f'BISHOP: {scalars["eg_bishop"]}, ROOK: {scalars["eg_rook"]}, ')
    lines.append(f'QUEEN: {scalars["eg_queen"]}, KING: 0}}\n\n')
    for name, const_name in SCALAR_TO_CONST.items():
        lines.append(f'{const_name} = {repr(scalars[name])}\n')
    for name, const_name in FLOAT_TO_CONST.items():
        lines.append(f'{const_name} = {repr(floats[name])}\n')
    lines.append('\n')
    lines.append('PASSED_PAWN_BONUS = [0, ')
    lines.append(', '.join(str(scalars[f'passed_pawn_rank{i}']) for i in range(2, 8)))
    lines.append(', 0]\n\n')
    for name in PSQT_NAMES:
        lines.extend(_format_list(name.upper(), psqt[name]))
    lines.append('PSQTs = {\n')
    lines.append('    PAWN:   (MG_PAWN,   EG_PAWN),\n')
    lines.append('    KNIGHT: (MG_KNIGHT, EG_KNIGHT),\n')
    lines.append('    BISHOP: (MG_BISHOP, EG_BISHOP),\n')
    lines.append('    ROOK:   (MG_ROOK,   EG_ROOK),\n')
    lines.append('    QUEEN:  (MG_QUEEN,  EG_QUEEN),\n')
    lines.append('    KING:   (MG_KING,   EG_KING),\n')
    lines.append('}\n')
    with open(_OUTPUT_PARAMETERS_PATH, 'w') as f:
        f.writelines(lines)


def coordinate_descent(positions, scalars, floats, psqt, K, max_passes):
    white_eval = make_eval_fn()
    apply_all(scalars, floats, psqt)
    best = mse(positions, white_eval, K)
    print(f'start MSE = {best:.6f} (K={K:.1f})', flush=True)
    save_best(scalars, floats, psqt, K, best)

    # scalar/psqt steps shrink each pass; floats use their own small steps
    int_steps = [8, 4, 2, 1]
    float_steps = [0.04, 0.02, 0.01]

    for p in range(max_passes):
        istep = int_steps[min(p, len(int_steps) - 1)]
        fstep = float_steps[min(p, len(float_steps) - 1)]
        improved = 0

        # scalar ints
        for name, default, lo, hi in SCALAR_PARAMS:
            for delta in (istep, -istep):
                v = scalars[name] + delta
                if v < lo or v > hi:
                    continue
                old = scalars[name]
                scalars[name] = v
                apply_scalars(scalars, floats)
                _eval.init_eval_tables()
                m = mse(positions, white_eval, K)
                if m < best - 1e-9:
                    best = m
                    improved += 1
                    break
                scalars[name] = old
            else:
                apply_scalars(scalars, floats)
                _eval.init_eval_tables()

        # float phase boundaries
        for name, default, lo, hi in FLOAT_PARAMS:
            for delta in (fstep, -fstep):
                v = round(floats[name] + delta, 4)
                if v < lo or v > hi:
                    continue
                old = floats[name]
                floats[name] = v
                apply_scalars(scalars, floats)
                _eval.init_eval_tables()
                m = mse(positions, white_eval, K)
                if m < best - 1e-9:
                    best = m
                    improved += 1
                    break
                floats[name] = old
            else:
                apply_scalars(scalars, floats)
                _eval.init_eval_tables()

        # PSQT squares
        for name in PSQT_NAMES:
            base = _BASELINE_PSQT[name]
            arr = psqt[name]
            for sq in range(64):
                lo = base[sq] - PSQT_DELTA
                hi = base[sq] + PSQT_DELTA
                for delta in (istep, -istep):
                    v = arr[sq] + delta
                    if v < lo or v > hi:
                        continue
                    old = arr[sq]
                    arr[sq] = v
                    apply_psqt(psqt)
                    _eval.init_eval_tables()
                    m = mse(positions, white_eval, K)
                    if m < best - 1e-9:
                        best = m
                        improved += 1
                        break
                    arr[sq] = old
                else:
                    apply_psqt(psqt)
                    _eval.init_eval_tables()

        # refit K periodically — eval scale drifts as params move
        K, _ = fit_k(positions, white_eval)
        best = mse(positions, white_eval, K)
        save_best(scalars, floats, psqt, K, best)
        print(f'pass {p+1}/{max_passes}: MSE={best:.6f} K={K:.1f} '
              f'improvements={improved} (istep={istep})', flush=True)

        if improved == 0 and istep == 1:
            print('converged (no improvement at step 1)', flush=True)
            break

    return best, K


_BASELINE_PSQT = None


def main():
    global _BASELINE_PSQT

    fens_file = sys.argv[1] if len(sys.argv) > 1 else 'tune/fens_sf_all.txt'
    cap       = int(sys.argv[2]) if len(sys.argv) > 2 else 60000
    max_passes = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    if not os.path.exists(fens_file):
        print(f'fEN file not found: {fens_file}')
        sys.exit(1)

    _BASELINE_PSQT = {name: list(getattr(_params, name.upper())) for name in PSQT_NAMES}

    positions = load_dataset(fens_file, cap)

    scalars = {name: d for name, d, lo, hi in SCALAR_PARAMS}
    floats = {name: d for name, d, lo, hi in FLOAT_PARAMS}
    psqt = {name: list(_BASELINE_PSQT[name]) for name in PSQT_NAMES}

    apply_all(scalars, floats, psqt)
    white_eval = make_eval_fn()
    K, k_mse = fit_k(positions, white_eval)
    print(f'fitted K = {K:.1f} (MSE={k_mse:.6f})', flush=True)

    n_params = len(SCALAR_PARAMS) + len(FLOAT_PARAMS) + len(PSQT_NAMES) * 64
    print(f'coordinate descent: {n_params} params, {len(positions)} positions, '
          f'{max_passes} passes\n', flush=True)

    best, K = coordinate_descent(positions, scalars, floats, psqt, K, max_passes)
    print(f'\nBest MSE: {best:.6f} (K={K:.1f})')
    save_best(scalars, floats, psqt, K, best)
    print(f'saved: {_OUTPUT_PARAMS_PATH} + {_OUTPUT_PARAMETERS_PATH}')


if __name__ == '__main__':
    main()
