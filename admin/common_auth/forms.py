from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.forms import ModelForm

class LoginForm(forms.Form):
    username = forms.CharField(label=(u'User Name'))
    password = forms.CharField(label=(u'Password'), widget=forms.PasswordInput(render_value=False))

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if not username or not password:
            raise forms.ValidationError("Please enter the missing information.")
            return self.cleaned_data
        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError("Invalid username/password combination. Please try again.")
        return self.cleaned_data
