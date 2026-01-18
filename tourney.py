from gui.tournament import Tournament
from gui.config import Config

if __name__ == '__main__':
    new = 'fixed/engine.bat'
    old = 'sophia/engine.bat'

    n_bullet = 15
    n_blitz = 20
    n_rapid = 10

    bullet_1_0 = Config(engine_1_path=new, engine_2_path=old, time_control=1 * 60, increment=0, total_games=n_bullet) # 1 + 0
    blitz_3_0 = Config(engine_1_path=new, engine_2_path=old, time_control=3 * 60, increment=0, total_games=n_blitz) # 3 + 0
    rapid_5_5 = Config(engine_1_path=new, engine_2_path=old, time_control=5 * 60, increment=5, total_games=n_rapid) # 5 + 5

    bullet_2_1 = Config(engine_1_path=new, engine_2_path=old, time_control=2 * 60, increment=1, total_games=n_bullet) # 2 + 1
    blitz_3_2 = Config(engine_1_path=new, engine_2_path=old, time_control=3 * 60, increment=0, total_games=n_blitz) # 3 + 2
    rapid_10_1 = Config(engine_1_path=new, engine_2_path=old, time_control=10 * 60, increment=1, total_games=n_rapid) # 10 + 1

    for settings in [bullet_1_0, blitz_3_0, rapid_5_5, bullet_2_1, blitz_3_2, rapid_10_1] * 2:
        tourney = Tournament(settings)
        tourney.run()