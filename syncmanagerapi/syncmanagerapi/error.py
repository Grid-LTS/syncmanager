class InvalidRequest(Exception):
    status_code = 400

    def __init__(self, message, field, status_code=None):
        Exception.__init__(self)
        self.message = message
        self.field = field
        if status_code is not None:
            self.status_code = status_code

    def get_response_info(self):
        rv = dict()
        rv['message'] = self.message
        rv['field'] = self.field
        return rv



