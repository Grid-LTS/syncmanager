from flask import Flask, request, Response
import os
import MySQLdb

from .settings import read_properties_file


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    # import all modules that need app context
    with app.app_context():
        from .error import InvalidRequest

    app.config.from_mapping(**read_properties_file())
    
    @app.route('/rest/syncdir', methods=['POST'])
    def parse_request():
        body = request.data
        if not body:
            raise InvalidRequest('Provide target directory path \'target_dir\' payload', 'target_dir')
        data = request.get_json(force=True)
        if not data['target_dir']:
            raise InvalidRequest('Provide target directory path \'target_dir\' payload', 'target_dir')
        target_dir = data['target_dir']
        if not os.path.exists(target_dir):
            try:
                oldmask = os.umask(0o002)
                os.makedirs(target_dir)
                os.umask(oldmask)
            except PermissionError:
                raise InvalidRequest('No permissions to create resource {}'.format(target_dir), 'target_dir', 403)
        return Response(status=201)

    return app


def initialize_database(app):
    db = MySQLdb.connect(host=app.config['DB_HOST'], user=app.config['DB_USER'],
                        passwd=app.config['DB_PASSWORD'], db=app.config['DB_SCHEMA_NAME'])
    cur = db.cursor()
    cur.execute("SHOW TABLES")
    if not cur.fetchall():
        print('Initialize database schema')
    db.close()


def main():
    app = create_app()
    initialize_database(app)
    app.run(debug=True)
