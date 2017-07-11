from django import forms

from osf.models import SpamStatus


class ConfirmForm(forms.Form):
    confirm = forms.ChoiceField(
        choices=[(SpamStatus.SPAM, 'Spam'), (SpamStatus.HAM, 'Ham')],
        widget=forms.RadioSelect(),
    )
