from django.views.generic.edit import FormView

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

    def get_context_data(self, **kwargs):
        user_kwargs = super(UserFormView, self).get_context_data(**kwargs)
        user_kwargs.setdefault(
            'notes_form', OSFUserForm(initial={'osf_id': self.guid}))
        return user_kwargs

    @property
    def success_url(self):
        return reverse_user(self.guid)


class OSFUserFormView(FormView):
    template_name = 'users/user.html'
    form_class = OSFUserForm

    def form_valid(self, form):
        print 'Here!'
        super(OSFUserFormView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse_user(None)
