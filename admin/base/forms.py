from django import forms


class GuidForm(forms.Form):
    guid = forms.CharField(label='Guid', max_length=5,
                           required=True)  # TODO: Move max to 6 when needed
