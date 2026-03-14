

class InvalidArgument(Exception):

    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

class ConfigurationError(Exception):

    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
