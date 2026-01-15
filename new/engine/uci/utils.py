def send_command(command : str) -> str:
    print(command, flush=True)

def send_info_string(string : str) -> str:
    send_command(f'info string {string}')