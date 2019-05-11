from flask import jsonify
import MySQLdb
import connexion

from .settings import read_properties_file, project_dir
from .utils import generate_password
from .error import InvalidRequest 


def create_app(test_config=None):
    # Create the application instance
    application = connexion.App(__name__, specification_dir=project_dir)
    # Read the swagger.yml file to configure the endpoints
    application.add_api('swagger.yaml')
    app = application.app
    app.config.from_mapping(**read_properties_file())

    # import all modules that need app context
    @app.errorhandler(InvalidRequest)
    def handle_invalid_usage(error):
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


def main():
    app = create_app()
    initialize_database(app)
    app.run(debug=True)
