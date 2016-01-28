from django import forms


class NodeForm(forms.Form):
    guid = forms.CharField(label='Guid', max_length=5, required=True)
