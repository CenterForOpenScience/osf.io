from django import forms


class AddSystemTagForm(forms.Form):
    system_tag_to_add = forms.CharField(label='system_tag_to_add', min_length=1, max_length=1024, required=True)
