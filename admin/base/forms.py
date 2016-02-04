from django import forms


class GuidForm(forms.Form):
    guid = forms.CharField(label='Guid', max_length=5, required=True)
