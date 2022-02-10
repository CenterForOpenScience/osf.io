from django import forms

class SearchForm(forms.Form):
    guid = forms.CharField(max_length=50,
                            required=False,
                            widget=forms.TextInput(attrs={'class': 'form-control'}),
                            label='guid:')
    name = forms.CharField(max_length=50,
                            required=True,
                            widget=forms.TextInput(attrs={'class': 'form-control'}),
                            label='name:')
    email = forms.CharField(max_length=50,
                            required=True,
                            widget=forms.TextInput(attrs={'class': 'form-control'}),
                            label='email:')