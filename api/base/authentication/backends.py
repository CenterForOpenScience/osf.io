from framework.auth.core import get_user, User

# https://docs.djangoproject.com/en/1.8/topics/auth/customizing/
class ODMBackend(object):

    def authenticate(self, username=None, password=None):
        return get_user(email=username, password=password) or None

    def get_user(self, user_id):
        return User.load(user_id)
