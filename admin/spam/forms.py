from django import forms

from website.project.spam.model import SpamStatus


class ConfirmForm(forms.Form):
    confirm = forms.ChoiceField(
        choices=[(SpamStatus.SPAM, 'Spam'), (SpamStatus.HAM, 'Ham')],
        widget=forms.RadioSelect(),
    )
