
class GitClientBase:

    def __init__(self, gitrepo = None):
        self.gitrepo = gitrepo

    def close(self):
        if self.gitrepo:
            self.gitrepo.close()
