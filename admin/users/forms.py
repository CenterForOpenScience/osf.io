from django import forms


class UserForm(forms.Form):
    guid = forms.CharField(label='Guid', max_length=5, required=True)
