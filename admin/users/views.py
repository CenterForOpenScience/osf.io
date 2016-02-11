from django.views.generic.edit import FormView
from django.core.urlresolvers import reverse

from website.project.model import User

from admin.base.views import GuidFormView
from admin.users.templatetags.user_extras import reverse_user
from .serializers import serialize_user
from .forms import OSFUserForm


class UserFormView(GuidFormView):
    template_name = 'users/user.html'
    object_type = 'user'

    def get_guid_object(self):
        return serialize_user(User.load(self.guid))

    @property
    def success_url(self):
        return reverse_user(self.guid)


class TestFormView(FormView):
    template_name = 'users/notes.html'
    form_class = OSFUserForm
    success_url = reverse('users:user')
