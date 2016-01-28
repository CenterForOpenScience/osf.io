from django.views.generic import FormView

from .forms import UserForm


class UserFormView(FormView):
    form_class = UserForm
    template_name = 'users/user.html'
