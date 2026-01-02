from gui.tournament import Tournament
from gui.config import Config

if __name__ == '__main__':
    new = 'claude 2/engine.bat'
    old = 'claude/engine.bat'
    n_bullet = 1
    n_blitz = 1
    n_rapid = 20

    bullet = Config(engine_1_path=new, engine_2_path=old, time_control=1 * 60, increment=0, total_games=n_bullet) # 1 + 0
    blitz = Config(engine_1_path=new, engine_2_path=old, time_control=3 * 60, increment=1, total_games=n_blitz) # 3 + 1
    rapid = Config(engine_1_path=new, engine_2_path=old, time_control=10 * 60, increment=1, total_games=n_rapid) # 10 + 5

    for settings in [bullet, blitz, rapid]:
        tourney = Tournament(settings)
        tourney.run()