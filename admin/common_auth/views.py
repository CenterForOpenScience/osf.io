from django.contrib import messages
from django.contrib.auth import authenticate, logout as logout_user, login as auth_login
from django.contrib.auth.forms import PasswordResetForm
from django.shortcuts import render, redirect

from forms import LoginForm, CustomUserRegistrationForm
from .models import MyUser


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


# Permission restriction based on staff (only staff can register new users). Use is_staff boolean?
def register(request):
    if request.user.is_staff:
        if request.method == 'POST':
            form = CustomUserRegistrationForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                password = form.cleaned_data['password1']
                new_user = MyUser.objects.create_user(email=email, password=password)
                new_user.first_name = form.cleaned_data['first_name']
                new_user.last_name = form.cleaned_data['last_name']
                group_perms = form.cleaned_data['group_perms']

                for group in group_perms:
                    new_user.groups.add(group)

                new_user.save()
                reset_form = PasswordResetForm({'email': new_user.email}, request.POST)
                assert reset_form.is_valid()
                reset_form.save(
                    subject_template_name='common_auth/emails/account_creation_subject.txt',
                    email_template_name='common_auth/emails/invitation_email.html',
                    request=request
                )
                messages.success(request, 'Registration successful')  # add email reference here
                return redirect('auth:register')
            else:
                print(form.errors)
                context = {'form': form}
                return render(request, 'register.html', context, status=400)
        else:
            reg_form = CustomUserRegistrationForm()
            context = {'form': reg_form}
            return render(request, 'register.html', context)
    else:
        # Best way to inform user: pop-up alert or display message after redirect?
        messages.error(request, 'You do not have permission to access the registration page.')
        return redirect('auth:login')
