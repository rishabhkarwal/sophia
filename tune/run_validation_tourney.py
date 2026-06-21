import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from gui.config import Config
from gui.coordinator import ParallelTournament

if __name__ == '__main__':
    rounds = [
        (1 * 60,  0,  40),
        (3 * 60,  2,  80),
        (5 * 60,  5,  80),
        (10 * 60, 1,  80),
    ]

    for tc, inc, games in rounds:
        config = Config(
            engine_1_path='sophia_tuned/engine.sh',
            engine_2_path='sophia/engine.sh',
            time_control=tc,
            increment=inc,
            total_games=games,
        )
        ParallelTournament(config, headless=True).run()
