from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(label=(u'User Name'), required=True)
    password = forms.CharField(label=(u'Password'), widget=forms.PasswordInput(render_value=False), required=True)
