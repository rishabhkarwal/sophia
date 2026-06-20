from gui.config import Config
from gui.coordinator import ParallelTournament
from gui.sequential import SequentialTournament

if __name__ == '__main__':
    # 'tui' = parallel games with live ANSI dashboard
    # 'gui' = sequential games with pygame board
    # 'headless' = gui but with no terminal output
    mode = 'gui'

    # engines
    new = 'sophia/engine.sh'
    old = 'sophia/engine.sh'

    # rounds
    # (time_control_secs, increment_secs, total_games)
    rounds = [
        (1 * 60,  0, 5),    # bullet 1+0
        (2 * 60,  1, 5),    # bullet 2+1
        (3 * 60,  0, 5),     # blitz  3+0
        (3 * 60,  2, 5),     # blitz  3+2
        (5 * 60,  5, 5),     # rapid  5+5
        (10 * 60, 1, 5),     # rapid  10+1
    ]

    # run
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
        elif mode == 'headless':
            ParallelTournament(config, headless=True).run()
        else:
            ParallelTournament(config).run()
