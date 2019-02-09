from .main import main as entrypoint


# setup.py: main() is defined entrypoint of module, delegate call to actual main script in main.py
def main():
    entrypoint()
