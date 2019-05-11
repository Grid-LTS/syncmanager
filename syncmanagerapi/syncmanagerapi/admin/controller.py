from flask import request, Response, json


def create_standard_user():
    from ..error import InvalidRequest
    from ..utils import generate_password
    from ..model import User, Roles

    body = request.data
    if not body:
        raise InvalidRequest('Empty body', 'username')
    data = request.get_json(force=True)
    username = data['username']
    if not data.get('password', None):
        password = generate_password()
    else:
        password = data['password']
    User.add_user(_username=username, _password=password, _role=Roles.DEFAULT)
    resp_data = dict()
    resp_data['password'] = password
    return Response(response=json.dumps(resp_data), status=200, mimetype='application/json')
