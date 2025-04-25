
class GitClientBase:

    def __init__(self):
        self.gitrepo = None

    def close(self):
        if self.gitrepo:
            self.gitrepo.close()
