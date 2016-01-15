from django import forms


class EmailForm(forms.Form):
    author = forms.CharField(label='Author', max_length=100)
    email = forms.ChoiceField(label='Email')
    subject = forms.CharField(label='Subject', required=True)
    message = forms.CharField(label='Message', required=True,
                              widget=forms.Textarea(
                                  attrs={'class': 'col-lg-6 col-md-8 col-sm-12'}))

    def __init__(self, *args, **kwargs):
        choices = kwargs.get('initial', {}).get('email', [])
        self.base_fields['email'] = forms.ChoiceField(choices=choices)
        super(EmailForm, self).__init__(*args, **kwargs)
