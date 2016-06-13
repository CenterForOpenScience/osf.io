from __future__ import absolute_import

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group

from admin.common_auth.models import MyUser


class LoginForm(forms.Form):
    email = forms.CharField(label=u'Email', required=True)
    password = forms.CharField(
        label=u'Password',
        widget=forms.PasswordInput(render_value=False),
        required=True
    )


class UserRegistrationForm(UserCreationForm):
    group_perms = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(name='prereg_group'),
        widget=FilteredSelectMultiple('verbose name', is_stacked=False),
        required=False
    )

    class Meta:
            model = MyUser
            fields = ['password1', 'password2', 'first_name', 'last_name', 'email', 'is_active', 'is_staff',
            'is_superuser', 'groups', 'user_permissions', 'last_login', 'group_perms', 'osf_id']

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['osf_id'].required = True
