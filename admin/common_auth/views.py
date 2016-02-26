from django.views.generic import UpdateView
from django.contrib import messages
from django.contrib.auth import (
    authenticate, logout as logout_user, login as auth_login
)
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse_lazy

from forms import LoginForm, DeskUserForm


def login(request):
    if request.user.is_authenticated():
        return redirect('home')
    form = LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(username=email, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Email and/or Password incorrect. Please try again.')
            return redirect('auth:login')
    context = {'form': form}
    return render(request, 'login.html', context)


def logout(request):
    logout_user(request)
    return redirect('auth:login')


class DeskUserFormView(UpdateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('home')

    def get_object(self, queryset=None):
        return self.request.user
