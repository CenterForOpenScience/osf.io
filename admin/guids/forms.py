from django import forms


class ReassignGuidForm(forms.Form):
    justification = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        strip=True,
        label='Justification',
    )
