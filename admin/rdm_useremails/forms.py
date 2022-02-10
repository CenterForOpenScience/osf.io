from django import forms

class SearchForm(forms.Form):
    guid = forms.CharField(label='guid', min_length=5, max_length=5, required=False)  # TODO: Move max to 6 when needed
    name = forms.CharField(label='name:', required=False)
    email = forms.EmailField(label='email', required=False)