from django.views.generic import DetailView

from website.project.model import User

from admin.base.views import GuidFormView
from admin.users.templatetags.user_extras import reverse_user
from .serializers import serialize_user


class UserFormView(GuidFormView):
    template_name = 'users/search.html'
    object_type = 'user'

    def get_guid_object(self):
        return serialize_user(User.load(self.guid))

    @property
    def success_url(self):
        return reverse_user(self.guid)


class UserView(DetailView):
    template_name = 'users/user.html'
    context_object_name = 'user'

    def __init__(self):
        self.guid = None
        super(UserView, self).__init__()

    def get_object(self, queryset=None):
        self.guid = self.kwargs.get('guid', None)
        return serialize_user(User.load(self.guid))
