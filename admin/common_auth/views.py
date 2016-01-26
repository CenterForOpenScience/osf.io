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

def register(request):
    # Creates User, takes selected permissions and assigns it to user, then saves resetform for email invitation

    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password1']
            user = MyUser.objects.create_user(email=email, password=password)
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            # Send email invitation (set passwordreset form and save)






            # reset_form = PasswordResetForm({'email': user.email}, request.POST)
            # assert reset_form.is_valid()
            # reset_form.save(
            #     subject_template_name='common_auth/emails/account_creation_subject.txt',
            #     email_template_name='common_auth/emails/invitation_email.html',
            #     request=request
            # )
            messages.success(request, 'Registration successful') # add email reference here
            return redirect('auth:login')
        else:
            print(form.errors)
            context = {'form': form}
            return render(request, 'register.html', context)
    else:
        ''' User not submitting form, show blank registrations form '''
        form = CustomUserRegistrationForm()
        context = {'form': form}
        return render(request, 'register.html', context)
