from django import forms

from osf.models import RegistrationSchema


class RegistrationSchemaForm(forms.ModelForm):
    name = forms.CharField(max_length=100, required=False)
    schema_version = forms.IntegerField(required=False)
    schema = forms.FileField(widget=forms.ClearableFileInput(), required=False)


    class Meta:
        model = RegistrationSchema
        fields = ('name', 'schema_version', 'schema')
