import click
from flask.cli import with_appcontext
from passlib.hash import bcrypt
from .model import User, Roles


# register CLI command
@click.command('admin-create')
@click.option('--name')
@click.option('--password')
@with_appcontext
def create_admin_command(name, password):
    if not name:
        click.echo('Provide a name, option --name')
        exit(1)
    if not name:
        click.echo('Provide a password, option --password')
        exit(1)
    hashed_password = bcrypt.using(rounds=12).hash(password)
    User.add_user(_username=name, _password=hashed_password, _role=Roles.ADMIN)
    click.echo('Created user {}'.format(name))
