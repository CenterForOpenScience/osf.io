from django import forms


class RegistrationDateForm(forms.Form):
    registered_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control'}),
    )
