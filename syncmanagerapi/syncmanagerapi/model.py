from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

from .database import db, ma


class User(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def password(self):
        raise AttributeError('Not allowed')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def all_users():
        return User.query.all()

    @staticmethod
    def user_by_username(_username):
        return User.query.filter_by(username=_username).first()

    @staticmethod
    def add_user(_username, _role, _password):
        user = User.user_by_username(_username=_username)
        if not user:
            _id = uuid.uuid4()
            user = User(id=str(_id), username=_username, role=_role, password=_password)
        else:
            user.password = _password
            user.role = _role
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def has_role(username, role):
        user = User.user_by_username(username)
        if not user:
            return False
        if user.role == role:
            return True
        return False

    def __repr__(self):
        return '<User %r>' % self.username


class ClientEnv(db.Model):
    __tablename__ = "user_client_env"

    id = db.Column(db.String(36), primary_key=True)
    env_name = db.Column(db.String(100), nullable=False)
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))

    user = db.relationship(User, backref="client_envs")

    @staticmethod
    def add_client_env(_user_id, _env_name):
        client_env_entity = ClientEnv.query.filter_by(user_id=_user_id, env_name=_env_name) \
            .one_or_none()
        if not client_env_entity:
            _id = uuid.uuid4()
            client_env_entity = ClientEnv(id=str(_id), user_id=_user_id, env_name=_env_name)
            db.session.add(client_env_entity)
            db.session.commit()
        return client_env_entity

    @staticmethod
    def get_client_env(_user_id, _env_name):
        return ClientEnv.query.filter_by(user_id=_user_id, env_name=_env_name) \
            .first()


class ClientEnvSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ClientEnv
        sqla_session = db.session
        include_relationships = True

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        sqla_session = db.session
        include_relationships = True