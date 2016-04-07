from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import MyUser


class LoginForm(forms.Form):
    email = forms.CharField(label=u'Email', required=True)
    password = forms.CharField(
        label=u'Password',
        widget=forms.PasswordInput(render_value=False),
        required=True
    )


class CustomUserRegistrationForm(UserCreationForm):
    class Meta:
            model = MyUser
            fields = ['password', 'first_name', 'last_name', 'email', 'is_active', 'is_staff',
            'is_superuser', 'groups', 'user_permissions', 'last_login', ]

    def __init__(self, *args, **kwargs):
        super(CustomUserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
