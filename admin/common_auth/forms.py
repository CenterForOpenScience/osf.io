from django import forms

class LoginForm(forms.Form):
    email = forms.CharField(label=(u'Email'), required=True)
    password = forms.CharField(label=(u'Password'), widget=forms.PasswordInput(render_value=False), required=True)
