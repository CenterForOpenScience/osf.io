from django import forms
from django.utils.translation import ugettext_lazy as _


class UserEmailsSearchForm(forms.Form):
    guid = forms.CharField(label='guid', min_length=5, max_length=5, required=False)  # TODO: Move max to 6 when needed
    name = forms.CharField(label=_('name'), required=False)
    email = forms.EmailField(label=_('email'), required=False)
