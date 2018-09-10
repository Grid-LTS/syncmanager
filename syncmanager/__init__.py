from .main import main as entrypoint

# delegate call of main entrypoint to actual main script
def main():
    entrypoint()