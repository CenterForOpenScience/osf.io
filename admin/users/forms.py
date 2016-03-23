from django import forms

from admin.base.forms import GuidForm


class UserForm(GuidForm):
    name = forms.CharField(label='Name')
    email = forms.CharField(label='Email')
