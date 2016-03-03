from django import forms
from ckeditor.widgets import CKEditorWidget

from website.project.model import Comment


class EmailForm(forms.Form):
    author = forms.CharField(label='Author', max_length=100)
    email = forms.ChoiceField(label='Email')
    subject = forms.CharField(label='Subject', required=True)
    message = forms.CharField(label='Message', required=True,
                              widget=CKEditorWidget())

    def __init__(self, *args, **kwargs):
        choices = kwargs.get('initial', {}).get('email', [])
        self.base_fields['email'] = forms.ChoiceField(choices=choices)
        super(EmailForm, self).__init__(*args, **kwargs)


class ConfirmForm(forms.Form):
    confirm = forms.ChoiceField(
        choices=[(Comment.SPAM, 'Spam'), (Comment.HAM, 'Ham')],
        widget=forms.RadioSelect(),
    )
