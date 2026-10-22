import re

from django import forms

from osf.models import Preprint, PreprintProvider
from osf.utils.workflows import ReviewStates

DOI_RE = re.compile(r'^10\.\d{4,9}/\S+$')


class RecoverDeletedPreprintForm(forms.Form):
    """Inputs needed to recreate a preprint that was hard-deleted by the
    Create-New-Version bug (ENG-11012). The GUID and DOI are recreated exactly
    as they were so existing DOIs and links keep resolving.
    """
    provider = forms.ModelChoiceField(queryset=PreprintProvider.objects.all())
    guid = forms.CharField(max_length=5, min_length=5, label='Base GUID')
    title = forms.CharField(max_length=512)
    description = forms.CharField(widget=forms.Textarea, required=False)
    use_new_guid = forms.BooleanField(
        required=False,
        label='GUID is taken: generate a new GUID',
        help_text='Only use if the original GUID now belongs to another object. A new GUID is generated, '
                  'so also fill in the original DOI to keep it.',
    )
    original_doi = forms.CharField(
        required=False,
        max_length=255,
        label='Original DOI',
        help_text='Optional: the preprint\'s original DOI (e.g. 10.31219/osf.io/abcde_v1), attached to the '
                  'recreated version. Needed when using a new GUID, since DOIs are otherwise derived from the GUID.',
    )
    file_guid = forms.CharField(
        required=False,
        label='Source file or preprint GUID',
        help_text='Optional: an existing file GUID, or a preprint GUID (e.g. abcde or abcde_v1) whose '
                  'primary file is used. The latest version of the file is copied into this version '
                  'as the primary file.',
    )
    ticket_reference = forms.CharField(
        max_length=255,
        label='Support ticket / JIRA reference',
        help_text='Recorded in the admin log so the recreated preprint is traceable.',
    )

    def clean_original_doi(self):
        doi = self.cleaned_data['original_doi'].strip()
        doi = re.sub(r'^(https?://(dx\.)?doi\.org/|doi:)', '', doi, flags=re.IGNORECASE)
        if doi and not DOI_RE.match(doi):
            raise forms.ValidationError('Enter a DOI like 10.31219/osf.io/abcde_v1.')
        return doi

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('original_doi') and not cleaned.get('use_new_guid'):
            self.add_error(
                'original_doi',
                'Only needed with a new GUID; with the original GUID the DOI is derived from it.',
            )
        return cleaned

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
