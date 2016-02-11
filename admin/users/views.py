from django.shortcuts import redirect

from website.project.model import User

from admin.base.views import GuidFormView
from admin.users.templatetags.user_extras import reverse_user
from .serializers import serialize_user


def disable_user(request, guid):
    user = User.load(guid)
    user.disable_account()
    return redirect(reverse_user(guid))


class UserFormView(GuidFormView):
    template_name = 'users/user.html'
    object_type = 'user'

    def get_guid_object(self):
        return serialize_user(User.load(self.guid))

    @property
    def success_url(self):
        return reverse_user(self.guid)
