from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, logout as logout_user, login as auth_login, views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

from forms import LoginForm

def login(request):
    if request.user.is_authenticated():
        return redirect('/admin/auth/home/')
    form = LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        admin_user = authenticate(username=username, password=password)
        if admin_user:
            auth_login(request, admin_user)
            return redirect('/admin/auth/home/')
        else:
            return redirect('/admin/auth/login/')
    context = {'form': form}
    return render(request, 'login.html', context)

def logout(request):
    logout_user(request)
    return redirect('/admin/auth/login/')