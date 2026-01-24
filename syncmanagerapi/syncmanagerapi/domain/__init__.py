class DatabaseConflict(Exception):


    def __init__(self, message):
        Exception.__init__(self)
        self.message = message


class DataInconsistencyException(Exception):
    status_code = 500

    def __init__(self, message, status_code=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def get_response_info(self):
        rv = dict()
        rv['message'] = self.message
        return rv