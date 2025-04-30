from flask import request, make_response, jsonify, json

from ..authorization import Roles

def get_standard_users():
    from ..model import User, UserSchema
    # check that user has ADMIN privileges
    from ..decorators import requires_auth_roles
    requires_auth_roles(Roles.ADMIN)
    resp_data = User.all_users()
    schema = UserSchema(many=True)
    return make_response(jsonify(schema.dump(resp_data)), 200)

def create_standard_user():
    from ..error import InvalidRequest
    from ..utils import generate_password
    from ..model import User, UserSchema
    # check that user has ADMIN privileges
    from ..decorators import requires_auth_roles
    requires_auth_roles(Roles.ADMIN)
    body = request.data
    if not body:
        raise InvalidRequest('Empty body', 'username')
    data = request.get_json(force=True)
    username = data['username']
    if not data.get('password', None):
        password = generate_password()
    else:
        password = data['password']
    db_user = User.add_user(_username=username, _password=password, _role=Roles.DEFAULT)
    schema = UserSchema()
    resp_data = schema.dump(db_user)
    resp_data['password'] = password
    return make_response(resp_data, 200)
