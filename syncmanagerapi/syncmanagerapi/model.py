from .database import db
from werkzeug.security import generate_password_hash, check_password_hash

import uuid


class Roles:
    ADMIN = 'ADMIN'
    DEFAULT = 'DEFAULT'


class User(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    @property
    def password(self):
        raise AttributeError('Not allowed')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def add_user(_username, _role, _password):
        _id = uuid.uuid4()
        new_user = User(id=_id, username=_username, role=_role, password=_password)
        db.session.add(new_user)
        db.session.commit()

    def __repr__(self):
        return '<User %r>' % self.username
