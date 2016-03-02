from django import forms

from website.project.model import Comment


class ConfirmForm(forms.Form):
    confirm = forms.ChoiceField(
        choices=[(Comment.SPAM, 'Spam'), (Comment.HAM, 'Ham')],
        widget=forms.RadioSelect(),
    )
