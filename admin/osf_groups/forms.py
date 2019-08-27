from django import forms


class OSFGroupSearchForm(forms.Form):
    name = forms.CharField(label='name', required=False)
    id = forms.CharField(label='id', required=False)
