from __future__ import absolute_import

from django.views.generic.edit import FormView
from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import login, REDIRECT_FIELD_NAME, authenticate, logout
from django.shortcuts import redirect, resolve_url, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.conf import settings

from admin.common_auth.forms import LoginForm, CustomUserRegistrationForm
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
        if not redirect_to:
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
        return redirect_to


def logout_user(request):
    logout(request)
    return redirect('auth:login')


def register(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access the registration page.')
        return redirect('auth:login')

    if request.method != 'POST':
        reg_form = CustomUserRegistrationForm()
        context = {'form': reg_form}
        return render(request, 'register.html', context)

    reg_form = CustomUserRegistrationForm(request.POST)
    if not reg_form.is_valid():
        context = {'form': reg_form}
        return render(request, 'register.html', context, status=400)

    email = reg_form.cleaned_data['email']
    password = reg_form.cleaned_data['password1']
    new_user = MyUser.objects.create_user(email=email, password=password)
    new_user.first_name = reg_form.cleaned_data['first_name']
    new_user.last_name = reg_form.cleaned_data['last_name']
    group_perms = reg_form.cleaned_data['group_perms']

    for group in group_perms:
        new_user.groups.add(group)

    new_user.save()
    reset_form = PasswordResetForm({'email': new_user.email}, request.POST)
    assert reset_form.is_valid()
    reset_form.save(
        subject_template_name='emails/account_creation_subject.txt',
        email_template_name='emails/password_reset_email.html',
        request=request
    )
    messages.success(request, 'Registration successful')
    return redirect('auth:register')
