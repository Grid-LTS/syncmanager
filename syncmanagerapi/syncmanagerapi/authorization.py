class Roles:
    ADMIN = 'ADMIN'
    DEFAULT = 'DEFAULT'


class InvalidAuthorizationException(Exception):

    def __init__(self, status_code = 403, message=''):
        Exception.__init__(self)
        self.status_code = status_code
        if message:
            self.message = message
            return
        if status_code == 401:
            self.message = 'You are not authenticated'
        self.message = 'You are not authorized'

    def get_response_info(self):
        rv = dict()
        rv['message'] = self.message
        return rv
