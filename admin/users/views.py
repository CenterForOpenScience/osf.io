from django.views.generic.edit import FormView

from website.project.model import User

from admin.base.views import GuidFormView, GuidView
from admin.users.templatetags.user_extras import reverse_user
from .serializers import serialize_user
from .forms import OSFUserForm


class UserFormView(GuidFormView):
    template_name = 'users/search.html'
    object_type = 'user'

    @property
    def success_url(self):
        return reverse_user(self.guid)


class OSFUserFormView(FormView):
    template_name = 'users/notes.html'
    form_class = OSFUserForm

    def __init__(self):
        self.guid = None
        super(OSFUserFormView, self).__init__()

    def get_context_data(self, **kwargs):
        self.guid = self.kwargs.get('guid', None)
        return super(OSFUserFormView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        self.guid = form.cleaned_data('guid').strip()
        super(OSFUserFormView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse_user(self.guid)


class UserView(GuidView):
    template_name = 'users/user.html'
    context_object_name = 'user'

    def get_object(self, queryset=None):
        self.guid = self.kwargs.get('guid', None)
        return serialize_user(User.load(self.guid))
