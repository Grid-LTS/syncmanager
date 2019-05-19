class Roles:
    ADMIN = 'ADMIN'
    DEFAULT = 'DEFAULT'


class InvalidAuthorizationException(Exception):
    status_code = 403

    def __init__(self, message=''):
        Exception.__init__(self)
        if message:
            self.message = message
        else:
            self.message = 'You are not authorized'

    def get_response_info(self):
        rv = dict()
        rv['message'] = self.message
        return rv
