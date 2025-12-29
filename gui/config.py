from dataclasses import dataclass

@dataclass
class Config:
    engine_1_path: str = "sophia/engine.bat"
    engine_2_path: str = "sophia/engine.bat"
    
    time_control: int = 60 # seconds
    increment: int = 0 # seconds
    total_games: int = 10 