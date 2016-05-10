from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse
from django.views.generic.edit import FormView
from django.contrib import messages
from password_reset.forms import PasswordRecoveryForm
from password_reset.views import Recover
from django.contrib.auth import login, REDIRECT_FIELD_NAME, authenticate, logout
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.http import Http404

from website.project.model import User
from website.settings import PREREG_ADMIN_TAG

from admin.base.utils import SuperUser
from admin.common_auth.forms import LoginForm, UserRegistrationForm
from admin.common_auth.models import MyUser


class LoginView(FormView):
    form_class = LoginForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'login.html'

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = authenticate(
            username=form.cleaned_data.get('email').strip(),
            password=form.cleaned_data.get('password').strip()
        )
        if user is not None:
            login(self.request, user)
        else:
            messages.error(
                self.request,
                'Email and/or Password incorrect. Please try again.'
            )
            return redirect('auth:login')
        return super(LoginView, self).form_valid(form)

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        if not redirect_to or redirect_to == '/':
            redirect_to = reverse('home')
        return redirect_to


def logout_user(request):
    logout(request)
    return redirect('auth:login')


class RegisterUser(SuperUser, FormView):
    form_class = UserRegistrationForm
    template_name = 'register.html'

    def form_valid(self, form):
        osf_id = form.cleaned_data.get('osf_id')
        osf_user = User.load(osf_id)
        try:
            osf_user.system_tags.append(PREREG_ADMIN_TAG)
        except AttributeError:
            raise Http404(('OSF user with id "{}" not found.'
                           ' Please double check.').format(osf_id))
        new_user = MyUser.objects.create_user(
            email=form.cleaned_data.get('email'),
            password=form.cleaned_data.get('password1')
        )
        new_user.first_name = form.cleaned_data.get('first_name')
        new_user.last_name = form.cleaned_data.get('last_name')
        new_user.osf_id = osf_id
        for group in form.cleaned_data.get('group_perms'):
            new_user.groups.add(group)
        new_user.save()
        reset_form = PasswordRecoveryForm(
            data={'username_or_email': new_user.email}
        )
        if reset_form.is_valid():
            send = Recover()
            send.request = self.request
            send.form_valid(reset_form)
        messages.success(self.request, 'Registration successful!')
        return super(RegisterUser, self).form_valid(form)

    def get_success_url(self):
        return reverse('auth:register')
