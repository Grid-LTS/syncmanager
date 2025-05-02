
class GitClientBase:

    def __init__(self, gitrepo = None):
        self.gitrepo = gitrepo
        self.errors = []

    def close(self):
        if self.gitrepo:
            self.gitrepo.close()
