"""compare multiple eval candidates head-to-head using fixed-node game matches"""

import argparse
import json
import logging
import multiprocessing
import os
import random
import sys
import tempfile
from pathlib import Path

import chess
import chess.engine

ROOT = Path(__file__).resolve().parents[1]
ENGINE_CMD = [str(ROOT / "sophia" / "engine.sh")]
OPENINGS_FILE = ROOT / "gui" / "assets" / "openings.txt"
NODES_PER_MOVE = 15000
MAX_PLIES = 300

logging.getLogger("chess.engine").setLevel(logging.CRITICAL)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_a")
    parser.add_argument("candidate_b")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260621)
    parser.add_argument("--out")
    return parser.parse_args()


def load_openings():
    with open(OPENINGS_FILE) as f:
        return [line.strip() for line in f if line.strip()]


def load_candidate(path):
    if path in ("baseline", "current", "none"):
        return None
    path = Path(path).resolve()
    if not path.exists():
        print(f"candidate not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def write_temp_candidate(candidate):
    if candidate is None:
        return None
    fd, path = tempfile.mkstemp(suffix=".json", prefix="sophia_cmp_")
    with os.fdopen(fd, "w") as f:
        json.dump(candidate, f)
    return path


def engine_env(params_path):
    env = dict(os.environ)
    if params_path:
        env["SOPHIA_TUNE_PARAMS"] = params_path
    else:
        env.pop("SOPHIA_TUNE_PARAMS", None)
    return env


def open_engines(path_a, path_b):
    eng_a = chess.engine.SimpleEngine.popen_uci(ENGINE_CMD, env=engine_env(path_a))
    eng_b = chess.engine.SimpleEngine.popen_uci(ENGINE_CMD, env=engine_env(path_b))
    return eng_a, eng_b


def quit_engine(eng):
    if eng is None: return
    try:
        eng.quit()
    except Exception:
        try:
            eng.close()
        except Exception:
            pass


def play_one(eng_a, eng_b, opening_fen, a_is_white, game_id):
    board = chess.Board(opening_fen + " 0 1")
    limit = chess.engine.Limit(nodes=NODES_PER_MOVE)

    while not board.is_game_over(claim_draw=True) and board.ply() < MAX_PLIES:
        stm = board.turn
        engine_is_a = (stm == chess.WHITE) == a_is_white
        eng = eng_a if engine_is_a else eng_b
        result = eng.play(board, limit, game=game_id)
        if result.move is None or result.move not in board.legal_moves:
            return 0.0 if engine_is_a else 1.0
        board.push(result.move)

    outcome = board.outcome(claim_draw=True)
    if outcome is None or outcome.winner is None:
        return 0.5
    a_won = (outcome.winner == chess.WHITE) == a_is_white
    return 1.0 if a_won else 0.0


def play_chunk(args):
    game_specs, path_a, path_b = args
    eng_a, eng_b = open_engines(path_a, path_b)
    scores = []
    try:
        for game_id, (fen, a_is_white) in enumerate(game_specs):
            try:
                scores.append(play_one(eng_a, eng_b, fen, a_is_white, game_id))
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError, BrokenPipeError):
                scores.append(0.0)
                quit_engine(eng_a)
                quit_engine(eng_b)
                eng_a, eng_b = open_engines(path_a, path_b)
    finally:
        quit_engine(eng_a)
        quit_engine(eng_b)
    return scores


def run_match(candidate_a, candidate_b, n_games, n_parallel, openings):
    path_a = write_temp_candidate(candidate_a)
    path_b = write_temp_candidate(candidate_b)
    try:
        games = []
        for _ in range(n_games // 2):
            fen = random.choice(openings)
            games.append((fen, True))
            games.append((fen, False))

        chunks = [[] for _ in range(n_parallel)]
        for i, game in enumerate(games):
            chunks[i % n_parallel].append(game)
        tasks = [(chunk, path_a, path_b) for chunk in chunks if chunk]

        with multiprocessing.Pool(len(tasks)) as pool:
            results = pool.map(play_chunk, tasks)
        scores = [score for chunk_scores in results for score in chunk_scores]
        return sum(scores), len(scores)
    finally:
        for path in (path_a, path_b):
            if path and os.path.exists(path):
                os.remove(path)


def default_out(path_a, path_b):
    stem_a = Path(path_a).stem
    stem_b = Path(path_b).stem
    return ROOT / "tune" / "reports" / f"{stem_a}_vs_{stem_b}_nodes_match.json"


def main():
    args = parse_args()
    random.seed(args.seed)
    candidate_a = load_candidate(args.candidate_a)
    candidate_b = load_candidate(args.candidate_b)
    openings = load_openings()
    score, played = run_match(candidate_a, candidate_b, args.games, args.parallel, openings)

    report = {
        "candidate_a": str(Path(args.candidate_a).resolve()) if candidate_a else "baseline",
        "candidate_b": str(Path(args.candidate_b).resolve()) if candidate_b else "baseline",
        "score_for_a": score,
        "games": played,
        "score_fraction_for_a": score / played,
        "nodes_per_move": NODES_PER_MOVE,
        "parallel": args.parallel,
        "seed": args.seed,
    }
    out_path = Path(args.out).resolve() if args.out else default_out(args.candidate_a, args.candidate_b)
    os.makedirs(out_path.parent, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps(report, indent=2))
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
