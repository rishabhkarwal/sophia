from dataclasses import dataclass
import os

@dataclass
class Config:
    engine_1_path: str = 'sophia/engine.sh'
    engine_2_path: str = 'sophia/engine.sh'
    engine_1_name: str = ''
    engine_2_name: str = ''
    time_control: int = 60      # seconds
    increment: int = 0
    total_games: int = 20
    workers: int = 0            # 0 = auto (cpu_count - 2)
    pgn_path: str = 'games.pgn'
    openings_file: str | None = None

    def __post_init__(self):
        if not self.engine_1_name:
            self.engine_1_name = os.path.basename(os.path.dirname(self.engine_1_path)) or 'engine1'
        if not self.engine_2_name:
            self.engine_2_name = os.path.basename(os.path.dirname(self.engine_2_path)) or 'engine2'
        if self.engine_1_name == self.engine_2_name:
            self.engine_1_name += '.1'
            self.engine_2_name += '.2'
        if self.workers <= 0:
            self.workers = max(1, (os.cpu_count() or 4) - 2)
        if self.total_games % 2 != 0:
            self.total_games += 1
