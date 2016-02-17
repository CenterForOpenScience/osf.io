from django import forms


class EmailResetForm(forms.Form):
    emails = forms.ChoiceField(label='Email')

    def __init__(self, *args, **kwargs):
        choices = kwargs.get('initial', {}).get('email', [])
        self.fields['email'] = forms.ChoiceField(choices=choices)
        super(EmailResetForm, self).__init__(*args, **kwargs)
