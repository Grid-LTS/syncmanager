import string
import secrets


def generate_password(length=12):
    pwchars = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(pwchars) for i in range(length))
    return password
