from django.core.urlresolvers import reverse

from website.project.model import User

from admin.abstract.views import GuidFormView
from .serializers import serialize_user
from .forms import UserForm


class UserFormView(GuidFormView):
    form_class = UserForm
    template_name = 'users/user.html'
    object_type = 'user'

    def get_guid_object(self):
        return serialize_user(User.load(self.guid))

    @property
    def success_url(self):
        return reverse('users:user') + '?guid={}'.format(self.guid)
