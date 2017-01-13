from __future__ import absolute_import

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Group

from osf.models.user import OSFUser
from admin.common_auth.models import AdminProfile


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
            model = OSFUser
            fields = ['given_name', 'username']

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['osf_id'].required = True


class DeskUserForm(forms.ModelForm):
    class Meta:
        model = AdminProfile
        fields = ['desk_token', 'desk_token_secret']
