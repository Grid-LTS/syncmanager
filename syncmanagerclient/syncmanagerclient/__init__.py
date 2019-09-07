from .main import main as entrypoint, legacy as legacy_entrypoint


# setup.py: main() is defined as entrypoint of module, delegate call
def main():
    entrypoint()


def legacy():
    legacy_entrypoint()
