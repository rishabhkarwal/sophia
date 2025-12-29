from gui.tournament import Tournament
from gui.config import Config

if __name__ == '__main__':
    config = Config(time_control=60, total_games=50)

    tourney = Tournament(config)
    tourney.run()