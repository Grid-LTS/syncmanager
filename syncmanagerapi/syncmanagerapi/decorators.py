from flask import current_app, request

from .model import User
from .authorization import InvalidAuthorizationException

def requires_auth():
    auth = request.authorization
    if not auth:
        raise InvalidAuthorizationException(401)

def requires_auth_roles(role):
    auth = request.authorization
    if not auth:
        raise InvalidAuthorizationException(401)
    if not User.has_role(auth.username, role):
        raise InvalidAuthorizationException()
