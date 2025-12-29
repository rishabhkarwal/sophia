from datetime import datetime
import os

if os.name == 'nt': os.system('')

class Colour:
    WHITE = '\033[97m'
    BLACK = '\033[30m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GREY = '\033[90m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def get_time():
    return datetime.now().strftime("%H:%M:%S") #[HH:MM:SS]

def log(message, colour=Colour.RESET):
    print(f'{colour}[{get_time()}]{Colour.RESET} {message}')

def log_error(message):
    log(message, Colour.RED)

def log_info(message):
    log(message, Colour.CYAN)