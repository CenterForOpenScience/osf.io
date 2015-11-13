from django import forms
from django.contrib.auth import authenticate

class LoginForm(forms.Form):
    username = forms.CharField(label=(u'User Name'), required=True)
    password = forms.CharField(label=(u'Password'), widget=forms.PasswordInput(render_value=False), required=True)
