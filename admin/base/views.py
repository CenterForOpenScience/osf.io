from django.contrib import messages
from django.contrib.auth import views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_decode

@login_required
def home(request):
    return render(request, 'home.html', {'user': request.user})

def password_reset_done(request, **kwargs):
    messages.success(request, 'You have successfully reset your password and activated your admin account. Thank you')
    return redirect('/admin/auth/login/')

def password_reset_confirm_custom(request, **kwargs):
    response = views.password_reset_confirm(request, **kwargs)
    # i.e. if the user successfully resets their password
    if response.status_code == 302:
        try:
            uid = urlsafe_base64_decode(kwargs['uidb64'])
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            pass
        else:
            user.is_active = True
            user.save()
    return response
