import os
from flask import jsonify
import MySQLdb
import connexion

from .settings import read_properties_file
from .utils import generate_password
from .error import InvalidRequest 
from .authorization import InvalidAuthorizationException


def create_app(test_config=None):
    # Create the application instance
    application = connexion.App(__name__, specification_dir=os.path.dirname(os.path.abspath(__file__)))
    # Read the swagger.yml file to configure the endpoints
    application.add_api('swagger.yaml')
    app = application.app
    app.config.from_mapping(**read_properties_file())
    app.config['BASIC_AUTH_FORCE'] = True

    with app.app_context():
        from .authentication import SyncBasicAuth
        basic_auth = SyncBasicAuth(app)

    # import all modules that need app context
    @app.errorhandler(InvalidRequest)
    def handle_invalid_usage(error):
        return handleError(error)

    @app.errorhandler(InvalidAuthorizationException)
    def handle_authentication_error(error):
        response = jsonify(error.get_response_info())
        response.status_code = error.status_code
        return response

    with app.app_context():
        from .cli import create_admin_command
        app.cli.add_command(create_admin_command)
    return app


def initialize_database(app):
    with app.app_context():
        from . import database
        db = MySQLdb.connect(host=app.config['DB_HOST'], user=app.config['DB_USER'],
                             passwd=app.config['DB_PASSWORD'], db=app.config['DB_SCHEMA_NAME'])
        cur = db.cursor()
        cur.execute("SHOW TABLES")
        if not cur.fetchall():
            database.init_schema()
        db.close()

def handleError(error):
    response = jsonify(error.get_response_info())
    response.status_code = error.status_code
    return response


def main():
    app = create_app()
    initialize_database(app)
    app.run(debug=True)
