from datetime import datetime
import os

# enable ANSI escape codes on Windows
if os.name == 'nt': os.system('')

class Colour:
    WHITE = '\033[97m'
    BLACK = '\033[30m'
    GREY = '\033[90m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def log(message, colour=Colour.RESET):
    print(f'{colour}[{get_time()}] {message}{Colour.RESET}')

def log_error(message):
    log(f"ERROR: {message}", Colour.RED)

def log_info(message):
    log(message, Colour.CYAN)

def log_gui(message):
    print(f'\n{Colour.GREY}[{get_time()}] [GUI] >> {message}{Colour.RESET}')

def log_engine(name, message, colour_code):
    print(f'{colour_code}[{get_time()}] [{name}] << {message}{Colour.RESET}')