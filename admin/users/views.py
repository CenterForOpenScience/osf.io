from django.views.generic import FormView
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound
from django.shortcuts import render

from website.project.model import User

from .serializers import serialize_user
from .forms import UserForm


class UserFormView(FormView):
    form_class = UserForm
    template_name = 'users/user.html'

    def __init__(self):
        self.guid = None
        super(UserFormView, self).__init__()

    def get(self, request, *args, **kwargs):
        self.guid = request.GET.get('guid', None)
        if self.guid is not None:
            try:
                user = serialize_user(User.load(self.guid))
            except (AttributeError, TypeError):
                return HttpResponseNotFound(
                    '<h1>User ({}) not found.</h1>'.format(self.guid)
                )
        else:
            user = None
        form = self.get_form()
        context = {
            'user': user,
            'form': form,
        }
        return render(request, self.template_name, context)

    def form_valid(self, form):
        self.guid = form.cleaned_data.get('guid').strip()
        return super(UserFormView, self).form_valid(form)

    def get_initial(self):
        self.initial = {
            'guid': self.guid,
        }
        return super(UserFormView, self).get_initial()

    @property
    def success_url(self):
        return reverse('users:user') + '?guid={}'.format(self.guid)
