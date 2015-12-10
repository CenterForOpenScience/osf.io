from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import MyUser

class LoginForm(forms.Form):
    email = forms.CharField(label=(u'Email'), required=True)
    password = forms.CharField(label=(u'Password'), widget=forms.PasswordInput(render_value=False), required=True)

class CustomUserRegistrationForm(UserCreationForm):
    class Meta:
            model = MyUser
            fields = ['password', 'first_name', 'last_name', 'email', 'is_active', 'is_staff',
            'is_superuser', 'groups', 'user_permissions', 'last_login', ]
    def __init__(self, *args, **kwargs):
        super(CustomUserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 5:
            raise ValidationError('Password is too short')
        if len(password) > 256:
            raise ValidationError('Password is too long')
        return password
