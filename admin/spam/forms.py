from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
import floppyforms as forms

class EmailForm(forms.Form):

    name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    subject = forms.CharField(required=True)
    message = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Submit'))
        super(EmailForm, self).__init__(*args, **kwargs)
