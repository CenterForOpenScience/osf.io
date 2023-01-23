from django import forms


class EmailResetForm(forms.Form):
    emails = forms.ChoiceField(label='Email')

    def __init__(self, *args, **kwargs):
        choices = kwargs.get('initial', {}).get('emails', [])
        self.base_fields['emails'] = forms.ChoiceField(choices=choices)
        super().__init__(*args, **kwargs)


class UserSearchForm(forms.Form):
    guid = forms.CharField(label='guid', min_length=5, max_length=5, required=False)  # TODO: Move max to 6 when needed
    name = forms.CharField(label='name', required=False)
    email = forms.EmailField(label='email', required=False)


class MergeUserForm(forms.Form):
    user_guid_to_be_merged = forms.CharField(label='user_guid_to_be_merged', min_length=5, max_length=5, required=True)  # TODO: Move max to 6 when needed


class AddSystemTagForm(forms.Form):
    system_tag_to_add = forms.CharField(label='system_tag_to_add', min_length=1, max_length=1024, required=True)
