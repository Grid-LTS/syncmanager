import os
from flask import jsonify

import connexion

from .settings import project_dir, properties_dir, get_properties_path
from .utils import generate_password
from .error import InvalidRequest
from .authorization import InvalidAuthorizationException

from dotenv import load_dotenv

# .env file should only exists on developer machine, setting FLASK_ENV=development
dotenv_path = os.path.join(project_dir, '.env')  # Path to .env file
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def create_app(test_config=None):
    """
    entry point for wsgi process and Flask CLI commands 
    :param test_config: 
    :return: Flask instance
    """
    # Create the application instance
    application = connexion.App(__name__, specification_dir=os.path.dirname(os.path.abspath(__file__)))
    # Read the swagger.yml file to configure the endpoints
    application.add_api('swagger.yaml')
    app = application.app
    if not app.config.get('SYNCMANAGER_SERVER_CONF', None) and not test_config:
        app.config['SYNCMANAGER_SERVER_CONF'] = properties_dir
    if test_config:
        app.config.from_mapping(test_config)
    properties_file_path = get_properties_path(environment=app.env,
                                               _properties_dir=app.config['SYNCMANAGER_SERVER_CONF'])
    app.config.from_pyfile(properties_file_path, silent=True)
    if app.env == "development" or app.env == "test":
        app.config["INSTALL_DIR"] = os.path.join(app.config['SYNCMANAGER_SERVER_CONF'], "local")
        app.config["FS_ROOT"] = os.path.join(app.config["INSTALL_DIR"], "var")
    app.config["SQLALCHEMY_ECHO"] = True
    
    with app.app_context():
        from .authentication import SyncBasicAuth
        basic_auth = SyncBasicAuth(app)

    # import all modules that need app context
    @app.errorhandler(InvalidRequest)
    def handle_invalid_usage(error):
        return handle_error(error)

    @app.errorhandler(InvalidAuthorizationException)
    def handle_authentication_error(error):
        response = jsonify(error.get_response_info())
        response.status_code = error.status_code
        return response

    with app.app_context():
        from .cli import create_admin_command
        app.cli.add_command(create_admin_command)
    # initialize database tables
    initialize_database(app, reset=app.config.get("DB_RESET", False))
    return app


def initialize_database(app, reset=False):
    with app.app_context():
        from . import database
        if reset:
            # in test environment when module code is not reexecuted, we need to reset (empty) the database 
            database.reset_db_connection()
        db, db_type = database.get_database_connection(app)
        cur = db.cursor()
        if db_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table';"
        else:
            query = "SHOW TABLES"
        cur.execute(query)
        tables = ['user', 'user_client_env', 'git_repos', 'user_git_repos', 'user_gitrepo_clientenv']
        for existing_table in cur.fetchall():
            try:
                ind = tables.index(existing_table[0])
                del tables[ind]
            except ValueError:
                pass
        if len(tables) > 0:
            database.init_schema()
        db.close()


def handle_error(error):
    response = jsonify(error.get_response_info())
    response.status_code = error.status_code
    return response


def main():
    app = create_app()
    app.run(debug=True)
