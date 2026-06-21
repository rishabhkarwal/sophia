"""
search-parameter tuner for sophia using Optuna + self-play matches

texel tuning can't see search params — two engines with different LMR settings
produce identical static evals. so each trial plays a fast match: sophia/ with
trial params injected via SOPHIA_TUNE_PARAMS vs sophia/ without overrides.
objective = match score fraction, maximised

usage:
    python tune/search_tune.py [n_trials] [games_per_trial] [parallel_games]

    n_trials:       Optuna trials (default: 100)
    games_per_trial: games per match, even number (default: 400)
    parallel_games: concurrent games (default: 8)

fixed node-count games avoid wall-clock contention artifacts. best params are
written to tune/best_search_params_cython.json on each improvement. resumable
via tune/search_optuna_cython.db
"""

import json
import os
import random
import sys
import multiprocessing
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.environ.pop('SOPHIA_TUNE_PARAMS', None)
sys.path.insert(0, os.path.join(ROOT, 'sophia'))

import engine.core.parameters as _params

import chess
import chess.engine
import optuna
optuna.logging.set_verbosity(optuna.logging.INFO)

BASELINE_CMD = [os.path.join(ROOT, 'sophia', 'engine.sh')]
TRIAL_CMD    = [os.path.join(ROOT, 'sophia', 'engine.sh')]
OPENINGS_FILE = os.path.join(ROOT, 'gui', 'assets', 'openings.txt')
SEARCH_DB = os.path.join(ROOT, 'tune', 'search_optuna_cython.db')
SEARCH_PARAMS_OUT = os.path.join(ROOT, 'tune', 'best_search_params_cython.json')

# fixed nodes/move instead of a clock — contention-immune (see play_one). ~15k
# nodes is a few plies of real search, enough to separate search-param quality.
NODES_PER_MOVE = 15000
MAX_PLIES = 300


INT_PARAMS = [
    # pruning margins
    ('STATIC_NULL_MARGIN',       _params.STATIC_NULL_MARGIN,        60, 350),
    ('REVERSE_FUTILITY_MARGIN',  _params.REVERSE_FUTILITY_MARGIN,   60, 250),
    # razoring / futility margins handled as per-depth lists below
    # LMR
    ('LMR_MOVE_THRESHOLD',       _params.LMR_MOVE_THRESHOLD,         2,  10),
    ('LMR_MIN_DEPTH',            _params.LMR_MIN_DEPTH,              2,   5),
    ('LMR_HEAVY_THRESHOLD',      _params.LMR_HEAVY_THRESHOLD,        6,  20),
    ('LMR_HEAVY_REDUCTION',      _params.LMR_HEAVY_REDUCTION,        2,   4),
    # LMP
    ('LMP_BASE',                 _params.LMP_BASE,                   2,  10),
    ('LMP_MULTIPLIER',           _params.LMP_MULTIPLIER,             1,   4),
    ('LMP_DEPTH_CAP',            _params.LMP_DEPTH_CAP,              2,   6),
    # NMP
    ('NMP_BASE_REDUCTION',       _params.NMP_BASE_REDUCTION,         2,   4),
    ('NMP_DEPTH_REDUCTION',      _params.NMP_DEPTH_REDUCTION,        3,   5),
    ('NMP_EVAL_MARGIN',          _params.NMP_EVAL_MARGIN,          100, 450),
    ('NMP_DEEP_DEPTH',           _params.NMP_DEEP_DEPTH,             4,   9),
    # SEE / IID
    ('SEE_PRUNING_DEPTH_CAP',    _params.SEE_PRUNING_DEPTH_CAP,      3,   9),
    ('IID_MIN_DEPTH',            _params.IID_MIN_DEPTH,              3,   7),
    # aspiration
    ('ASPIRATION_MIN',           _params.ASPIRATION_MIN,            15, 100),
    ('ASPIRATION_MAX',           _params.ASPIRATION_MAX,           250, 900),
    # move ordering
    ('MOVE_REPETITION_PENALTY',  _params.MOVE_REPETITION_PENALTY, -100,   0),
]

FLOAT_PARAMS = [
    ('ASPIRATION_TIGHTEN_SCALE', _params.ASPIRATION_TIGHTEN_SCALE, 0.5, 0.95),
    # TIME_USAGE_LONG / TIME_USAGE_SHORT intentionally omitted: they are dead
    # under go nodes (only fire when nodes_limit is None) so tuning them here
    # adds noise to TPE without contributing signal.
]

# per-depth margin lists: (constant_name, defaults, low, high) for indices 1..3
LIST_PARAMS = [
    ('RAZOR_MARGIN',    list(_params.RAZOR_MARGIN),    200, 800),
    ('FUTILITY_MARGIN', list(_params.FUTILITY_MARGIN), 100, 700),
]


def load_openings():
    with open(OPENINGS_FILE) as f:
        return [line.strip() for line in f if line.strip()]


def _open_engines(params_path):
    trial_env = dict(os.environ, SOPHIA_TUNE_PARAMS=params_path)
    baseline_env = dict(os.environ)
    baseline_env.pop('SOPHIA_TUNE_PARAMS', None)
    trial = chess.engine.SimpleEngine.popen_uci(TRIAL_CMD, env=trial_env)
    baseline = chess.engine.SimpleEngine.popen_uci(BASELINE_CMD, env=baseline_env)
    return trial, baseline


def _quit(eng):
    if eng is None:
        return
    try:
        eng.quit()
    except Exception:
        try:
            eng.close()
        except Exception:
            pass


def play_one(trial_eng, baseline_eng, opening_fen, trial_is_white, game_id):
    """play a single game with already-open engines. game_id changes per game so
    python-chess emits `ucinewgame` (clears TT/killers) between games.

    Fixed NODES per move, not a clock: 10+ parallel games oversubscribe the cores,
    so wall-clock time control makes whichever engine searches *more* (the slower
    default baseline) accumulate wall time and forfeit — the tuner then "wins" by
    pruning hard enough to time the opponent out, a pure contention artifact (saw
    trials inflate to 0.94 while defaults stayed ~0.5). Node limits are immune to
    CPU contention: every move searches exactly NODES_PER_MOVE regardless of load,
    so the objective is genuinely 'better moves per node'."""
    board = chess.Board(opening_fen + ' 0 1')
    limit = chess.engine.Limit(nodes=NODES_PER_MOVE)

    while not board.is_game_over(claim_draw=True) and board.ply() < MAX_PLIES:
        stm = board.turn
        engine_is_trial = (stm == chess.WHITE) == trial_is_white
        eng = trial_eng if engine_is_trial else baseline_eng

        result = eng.play(board, limit, game=game_id)

        if result.move is None or result.move not in board.legal_moves:
            return 0.0 if engine_is_trial else 1.0
        board.push(result.move)

    outcome = board.outcome(claim_draw=True)
    if outcome is None or outcome.winner is None:
        return 0.5
    trial_won = (outcome.winner == chess.WHITE) == trial_is_white
    return 1.0 if trial_won else 0.0


def play_chunk(args):
    """play a list of games reusing one trial + one baseline engine. restarts an
    engine if it crashes (the crashing side forfeits that single game)"""
    game_specs, params_path = args  # list of (opening_fen, trial_is_white)

    trial_eng, baseline_eng = _open_engines(params_path)
    scores = []
    trial_crashed = False
    try:
        for game_id, (fen, trial_is_white) in enumerate(game_specs):
            try:
                scores.append(play_one(trial_eng, baseline_eng, fen, trial_is_white, game_id))
                trial_crashed = False
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError,
                    BrokenPipeError) as e:
                # identify which engine crashed by trying a ping; the one that
                # fails is the culprit and forfeits. unstable trial params that
                # crash should not be scored the same as a fair draw.
                trial_alive = True
                try:
                    trial_eng.ping()
                except Exception:
                    trial_alive = False
                score = 0.0 if not trial_alive else 1.0
                scores.append(score)
                _quit(trial_eng); _quit(baseline_eng)
                trial_eng, baseline_eng = _open_engines(params_path)
    finally:
        _quit(trial_eng); _quit(baseline_eng)
    return scores


def run_match(params, n_games, n_parallel, openings):
    fd, params_path = tempfile.mkstemp(suffix='.json', prefix='sophia_tune_')
    with os.fdopen(fd, 'w') as f:
        json.dump(params, f)

    try:
        # build the game list: each opening played twice (trial as W, then as B)
        games = []
        for _ in range(n_games // 2):
            fen = random.choice(openings)
            games.append((fen, True))
            games.append((fen, False))

        # split across workers so each worker reuses its engine pair for many games
        # (cuts engine spawns from 2*n_games to 2*n_parallel per trial)
        chunks = [[] for _ in range(n_parallel)]
        for i, g in enumerate(games):
            chunks[i % n_parallel].append(g)
        tasks = [(chunk, params_path) for chunk in chunks if chunk]

        with multiprocessing.Pool(len(tasks)) as pool:
            results = pool.map(play_chunk, tasks)
        scores = [s for chunk_scores in results for s in chunk_scores]
        return sum(scores), len(scores)
    finally:
        os.remove(params_path)



_openings = None
_n_games = 80
_n_parallel = 8


def objective(trial):
    params = {}
    for name, default, lo, hi in INT_PARAMS:
        params[name] = trial.suggest_int(name, lo, hi)
    for name, default, lo, hi in FLOAT_PARAMS:
        params[name] = trial.suggest_float(name, lo, hi)
    for name, defaults, lo, hi in LIST_PARAMS:
        # use delta params so Optuna models the true search space: each depth
        # margin is expressed as (base + delta_1 + delta_2 + ...) to guarantee
        # non-decreasing without the deceptive max() clipping that breaks TPE.
        depth_range = (hi - lo) // (len(defaults) - 1)
        vals = [0, lo + trial.suggest_int(f'{name}_base', 0, hi - lo)]
        for i in range(2, len(defaults)):
            delta = trial.suggest_int(f'{name}_d{i}', 0, depth_range)
            vals.append(vals[-1] + delta)
        params[name] = vals

    score, played = run_match(params, _n_games, _n_parallel, _openings)
    frac = score / played
    print(f'  trial {trial.number}: {score}/{played} = {frac:.3f}', flush=True)
    return frac


def save_best(study):
    trial = study.best_trial
    params = {}
    for name, default, lo, hi in INT_PARAMS:
        params[name] = trial.params[name]
    for name, default, lo, hi in FLOAT_PARAMS:
        params[name] = trial.params[name]
    for name, defaults, lo, hi in LIST_PARAMS:
        depth_range = (hi - lo) // (len(defaults) - 1)
        vals = [0, lo + trial.params[f'{name}_base']]
        for i in range(2, len(defaults)):
            vals.append(vals[-1] + trial.params[f'{name}_d{i}'])
        params[name] = vals

    with open(SEARCH_PARAMS_OUT, 'w') as f:
        json.dump({'score_fraction': trial.value, 'params': params}, f, indent=2)
    print(f'  saved: tune/best_search_params_cython.json (score={trial.value:.3f})', flush=True)


def main():
    global _openings, _n_games, _n_parallel

    n_trials   = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    _n_games   = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    _n_parallel = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    _openings = load_openings()

    study = optuna.create_study(
        direction='maximize',
        study_name='sophia_search_cython',
        storage=f'sqlite:///{SEARCH_DB}',
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(multivariate=True, n_startup_trials=15),
    )

    # baseline reference: all defaults — enqueue once so trial 0 measures the status quo
    if len(study.trials) == 0:
        defaults = {name: d for name, d, lo, hi in INT_PARAMS}
        defaults.update({name: d for name, d, lo, hi in FLOAT_PARAMS})
        for name, dvals, lo, hi in LIST_PARAMS:
            depth_range = (hi - lo) // (len(dvals) - 1)
            defaults[f'{name}_base'] = dvals[1] - lo
            for i in range(2, len(dvals)):
                defaults[f'{name}_d{i}'] = dvals[i] - dvals[i - 1]
        study.enqueue_trial(defaults)

    best_so_far = [-1.0]

    def callback(study, trial):
        if trial.value is not None and trial.value > best_so_far[0]:
            best_so_far[0] = trial.value
            save_best(study)

    n_params = len(INT_PARAMS) + len(FLOAT_PARAMS) + sum(len(d) - 1 for _, d, _, _ in LIST_PARAMS)
    print(f'search tuning: {n_trials} trials x {_n_games} games at {NODES_PER_MOVE} nodes/move, '
          f'{_n_parallel} parallel games, {n_params} params\n', flush=True)

    study.optimize(objective, n_trials=n_trials, callbacks=[callback])

    print(f'\nbest score: {study.best_value:.3f}')
    save_best(study)


if __name__ == '__main__':
    main()
