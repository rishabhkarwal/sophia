from dataclasses import dataclass

@dataclass
class Config:
    engine_1_path: str = 'sophia/engine.sh'
    engine_2_path: str = 'sophia/engine.sh'

    pgn_path: str = 'games.pgn'
    
    time_control: int = 60 # seconds
    increment: int = 0 # seconds
    total_games: int = 10 