from osf.models.user import OSFUser
from framework.auth.core import get_user, User
from django.contrib.auth.backends import ModelBackend

# https://docs.djangoproject.com/en/1.8/topics/auth/customizing/
class ODMBackend(ModelBackend):

    def authenticate(self, username=None, password=None):
        return get_user(email=username, password=password) or None

    def get_user(self, user_id):
        try:
            user = OSFUser.objects.get(id=user_id)
        except OSFUser.DoesNotExist:
            user = User.load(user_id)
        return user
