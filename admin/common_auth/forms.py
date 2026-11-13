import operator
from functools import reduce

from django import forms
from django.db.models import Q
from django.contrib.auth.models import Group

from osf.models import AdminProfile

# TODO: Moving to guardian, find a better way to distinguish "admin-like" groups from object permission groups
OBJECT_PERMISSION_GROUP_PREFIXES = (
    'collections_',
    'reviews_',
    'preprint_',
    'node_',
    'draft_registration_',
    'osfgroup_',
    'institution_',
)


def get_admin_app_groups():
    """Groups that grant admin app permissions (osf_admin, read_only, ...): every group but the per-object ones."""
    return Group.objects.exclude(
        reduce(operator.or_, (Q(name__startswith=prefix) for prefix in OBJECT_PERMISSION_GROUP_PREFIXES))
    )


class LoginForm(forms.Form):
    email = forms.CharField(label='Email', required=True)
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(render_value=False),
        required=True
    )


class UserRegistrationForm(forms.Form):
    """ A form that finds an existing OSF User, and grants permissions to that
    user so that they can use the admin app"""

    osf_id = forms.CharField(required=True, max_length=5, min_length=5)

    group_perms = forms.ModelMultipleChoiceField(
        queryset=get_admin_app_groups(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )


class DeskUserForm(forms.ModelForm):
    class Meta:
        model = AdminProfile
        fields = ['desk_token', 'desk_token_secret']


class TwoFactorForm(forms.Form):
    guid = forms.CharField(label='Guid', required=True, widget=forms.HiddenInput())
    code = forms.CharField(
        label='Two-Factor Code',
        required=True,
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'autocomplete': 'off'})
    )
