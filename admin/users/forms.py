from django import forms


class EmailResetForm(forms.Form):
    emails = forms.ChoiceField(label='Email')

    def __init__(self, *args, **kwargs):
        choices = kwargs.get('initial', {}).get('emails', [])
        self.base_fields['emails'] = forms.ChoiceField(choices=choices)
        super(EmailResetForm, self).__init__(*args, **kwargs)
