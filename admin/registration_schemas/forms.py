from django import forms

from osf.models import RegistrationSchema


class RegistrationSchemaCreateForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)
    schema = forms.FileField(widget=forms.ClearableFileInput(), required=False)

    class Meta:
        fields = ("name", "schema")


class RegistrationSchemaEditForm(forms.ModelForm):
    active = forms.BooleanField(required=False)
    visible = forms.BooleanField(required=False)

    class Meta:
        model = RegistrationSchema
        fields = ("active", "visible")
