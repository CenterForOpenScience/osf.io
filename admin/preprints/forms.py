from django import forms

from osf.models import Preprint, PreprintProvider
from osf.utils.workflows import ReviewStates


class RecoverDeletedPreprintForm(forms.Form):
    """Inputs needed to recreate a preprint that was hard-deleted by the
    Create-New-Version bug (ENG-11012). The GUID and DOI are recreated exactly
    as they were so existing DOIs and links keep resolving.
    """
    provider = forms.ModelChoiceField(queryset=PreprintProvider.objects.all())
    guid = forms.CharField(max_length=5, min_length=5, label='Base GUID')
    title = forms.CharField(max_length=512)
    description = forms.CharField(widget=forms.Textarea, required=False)
    file_guid = forms.CharField(
        required=False,
        label='Source file GUID',
        help_text='Optional: an existing file GUID; its latest version is copied into this '
                  'version as the primary file.',
    )
    ticket_reference = forms.CharField(
        max_length=255,
        label='Support ticket / JIRA reference',
        help_text='Recorded in the admin log so the recreated preprint is traceable.',
    )

class ChangeProviderForm(forms.ModelForm):
    class Meta:
        model = Preprint
        fields = ('provider',)


class MachineStateForm(forms.ModelForm):
    class Meta:
        model = Preprint
        fields = ('machine_state',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.is_public:
            self.fields['machine_state'].widget.attrs['disabled'] = 'disabled'
        else:
            if self.instance.machine_state == ReviewStates.INITIAL.db_name:
                self.fields['machine_state'].choices = [
                    (ReviewStates.INITIAL.value, ReviewStates.INITIAL.value),
                    (ReviewStates.PENDING.value, ReviewStates.PENDING.value),
                ]
            else:
                # Disabled Option you are on
                self.fields['machine_state'].widget.attrs['disabled'] = 'disabled'
                self.fields['machine_state'].choices = [
                    (self.instance.machine_state.title(), self.instance.machine_state)
                ]
