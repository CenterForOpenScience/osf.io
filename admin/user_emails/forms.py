from django import forms
from django.core.validators import validate_email, RegexValidator
from django.utils.translation import ugettext_lazy as _

guid_validator = RegexValidator('^([0-9a-z])+$',  # refer to osf.models.base.ALPHABET
                                message="User's GUID should be a combination of 5 Alphabets and Numbers")


class UserEmailsSearchForm(forms.Form):
    guid = forms.CharField(label='guid',
                           min_length=5, max_length=5,  # TODO: Move max to 6 when needed
                           validators=[guid_validator],
                           required=False)
    name = forms.CharField(label=_('name'), max_length=255, required=False)
    email = forms.EmailField(label=_('email'), min_length=6, max_length=255, required=False, validators=[validate_email])
