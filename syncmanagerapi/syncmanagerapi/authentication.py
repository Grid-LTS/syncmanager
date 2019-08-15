from flask_basicauth import BasicAuth

from .model import User


class SyncBasicAuth(BasicAuth):

    def __init__(self, app):
        BasicAuth.__init__(self, app)
        self.user = None

    def check_credentials(self, username, password):
        """
            authentication: validates users password
        """
        self.user = User.user_by_username(username)
        if not self.user:
            return False
        if not self.user.verify_password(password):
            return False
        return True
