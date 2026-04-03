from gui.config import Config
from gui.coordinator import ParallelTournament
from gui.sequential import SequentialTournament

if __name__ == '__main__':
    # ── mode ──────────────────────────────────────────
    # 'tui' = parallel games with live ANSI dashboard
    # 'gui' = sequential games with pygame board
    mode = 'tui'

    # ── engines ───────────────────────────────────────
    new = 'sophia/engine.sh'
    old = 'sophia/engine.sh'

    # ── rounds ────────────────────────────────────────
    # each entry is (time_control_secs, increment_secs, total_games)
    rounds = [
        (1 * 60,  0, 10),     # bullet 1+0
        (2 * 60,  1, 10),     # bullet 2+1
        (3 * 60,  0, 10),     # blitz  3+0
        (3 * 60,  2, 10),     # blitz  3+2
        (5 * 60,  5,  6),     # rapid  5+5
        (10 * 60, 1,  6),     # rapid  10+1
    ]

    # ── run ───────────────────────────────────────────
    for tc, inc, games in rounds:
        config = Config(
            engine_1_path=new,
            engine_2_path=old,
            time_control=tc,
            increment=inc,
            total_games=games,
        )

        if mode == 'gui':
            SequentialTournament(config).run()
        else:
            ParallelTournament(config).run()
