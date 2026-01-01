from gui.tournament import Tournament
from gui.config import Config

if __name__ == '__main__':
    new = 'sophia/engine.bat'
    old = 'indigo/engine.bat'
    n_games = 25

    bullet = Config(engine_1_path=new, engine_2_path=old, time_control=1 * 60, increment=0, total_games=n_games) # 1 + 0
    blitz = Config(engine_1_path=new, engine_2_path=old, time_control=3 * 60, increment=1, total_games=n_games) # 3 + 1
    rapid = Config(engine_1_path=new, engine_2_path=old, time_control=10 * 60, increment=5, total_games=n_games) # 10 + 5

    for settings in [bullet, blitz, rapid]:
        tourney = Tournament(settings)
        tourney.run()