from osf.models.user import OSFUser
from framework.auth.core import get_user
from django.contrib.auth.backends import ModelBackend


# https://docs.djangoproject.com/en/3.2/topics/auth/customizing/
class ODMBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        return get_user(email=username, password=password) or None

    def get_user(self, user_id):
        try:
            user = OSFUser.objects.get(id=user_id)
        except OSFUser.DoesNotExist:
            user = OSFUser.load(user_id)
        return user
