import click
from flask.cli import with_appcontext

from .model import User, Roles
from .utils import generate_password

# register CLI command
@click.command('admin-create')
@click.option('--name')
@click.option('--password')
@with_appcontext
def create_admin_command(name, password):
    if not name:
        click.echo('Provide a name, option --name')
        exit(1)
    if not password:
        password = generate_password()
        click.echo('Password is {}'.format(password))
    User.add_user(_username=name, _password=password, _role=Roles.ADMIN)
    click.echo('Created user {}'.format(name))
