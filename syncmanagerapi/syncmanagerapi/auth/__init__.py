from functools import wraps
from flask import current_app, jsonify, request

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        auth_service = current_app.config['auth']
        if not auth or not auth_service.check_credentials(auth.username, auth.password):
            return jsonify({'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function
