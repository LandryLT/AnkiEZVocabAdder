import os

def bold(text: str) -> str:
    return f'\033[1m{text}\033[0m'
def italic(text: str) -> str:
    return f'\033[3m{text}\033[0m'
def grey(text: str) -> str:
    return f'\033[2m{text}\033[0m'

def clearConsole():
    os.system('cls' if os.name == 'nt' else 'clear')

tqdm_bar_format = grey('{desc}: {percentage:3.0f}%|{bar:20}|')
