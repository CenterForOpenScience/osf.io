from django.views.generic.edit import FormView

from website.project.model import User

from admin.base.views import GuidFormView, GuidView
from admin.users.templatetags.user_extras import reverse_user
from .serializers import serialize_user
from .models import OSFUserForm, OSFUser


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
        self.model = None
        super(OSFUserFormView, self).__init__()

    def get_context_data(self, **kwargs):
        self.guid = self.kwargs.get('guid', None)
        try:
            self.model = OSFUser.objects.get(osf_id=self.guid)
        except OSFUser.DoesNotExist:
            self.model = OSFUser(osf_id=self.guid)
            self.model.save()
        kwargs.setdefault('osf_id', self.guid)
        return super(OSFUserFormView, self).get_context_data(**kwargs)

    def get_form(self, form_class=None):
        return self.form_class(instance=self.model, **self.get_form_kwargs())

    def form_valid(self, form):
        self.guid = form.cleaned_data.get('osf_id').strip()
        notes = form.cleaned_data.get('notes').strip()
        try:
            osf_user = OSFUser.objects.get(osf_id=self.guid)
            f = OSFUserForm(self.request.POST, instance=osf_user)
            f.save()
        except:
            new_user = OSFUser(osf_id=self.guid, notes=notes)
            new_user.save()
        return super(OSFUserFormView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse_user(self.guid)


class UserView(GuidView):
    template_name = 'users/user.html'
    context_object_name = 'user'

    def get_object(self, queryset=None):
        self.guid = self.kwargs.get('guid', None)
        return serialize_user(User.load(self.guid))
