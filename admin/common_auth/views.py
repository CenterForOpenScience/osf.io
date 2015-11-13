from django.contrib import messages
from django.contrib.auth import authenticate, logout as logout_user, login as auth_login
from django.shortcuts import render, redirect

from forms import LoginForm

def login(request):
    if request.user.is_authenticated():
        return redirect('/admin/')
    form = LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            auth_login(request, admin_user)
            return redirect('/admin/')
        else:
            messages.error(request, 'Username and/or Password incorrect. Please try again.')
            return redirect('/admin/auth/login/')
    context = {'form': form}
    return render(request, 'login.html', context)

def logout(request):
    logout_user(request)
    return redirect('/admin/auth/login/')
