from django.contrib import messages
from django.contrib.auth import authenticate, logout as logout_user, login as auth_login
from django.shortcuts import render, redirect

from forms import LoginForm, CustomUserRegistrationForm

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
    if request.user.is_authenticated():
        return redirect('auth:login')
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']
            user = User.objects.create_user(username=email,
                first_name=email, last_name=last_name, password=password)
            user.save()
            # Send email





            user = authenticate(username=email, password=password)
            auth_login(request, user)
            return redirect('auth:login')
        else:
            context = {'form': form}
            return render(request, 'register.html', context)
    else:
        ''' User not submitting form, show blank registrations form '''
        form = CustomUserRegistrationForm()
        context = {'form': form}
        return render(request, 'register.html', context)

