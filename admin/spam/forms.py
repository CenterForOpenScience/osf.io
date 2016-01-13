from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, Div
import floppyforms as forms


class EmailForm(forms.Form):

    name = forms.CharField(required=False)
    email = forms.ChoiceField(required=True)
    subject = forms.CharField(required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Submit'))
        choices = kwargs.get('initial', {}).get('email', [])
        self.base_fields['email'] = forms.ChoiceField(choices=choices)
        self.helper.layout = Layout(
            Field('name', readonly=True),
            'email',
            Div("User's primary email is default."),
            'subject',
            'message',
        )
        super(EmailForm, self).__init__(*args, **kwargs)
