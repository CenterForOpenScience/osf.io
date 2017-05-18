from django.forms import ModelForm, CheckboxSelectMultiple, MultipleChoiceField, HiddenInput, CharField

from osf.models import PreprintProvider, Subject
from admin.base.utils import get_subject_rules, get_toplevel_subjects, get_nodelicense_choices


class PreprintProviderForm(ModelForm):
    toplevel_subjects = MultipleChoiceField(widget=CheckboxSelectMultiple())
    subjects_chosen = CharField(widget=HiddenInput())

    class Meta:
        model = PreprintProvider

        exclude = ['modm_model_path', 'modm_query']

        widgets = {
            'licenses_acceptable': CheckboxSelectMultiple(),
            'subjects_acceptable': HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        toplevel_choices = get_toplevel_subjects()
        nodelicense_choices = get_nodelicense_choices()
        super(PreprintProviderForm, self).__init__(*args, **kwargs)
        self.fields['toplevel_subjects'].choices = toplevel_choices
        self.fields['licenses_acceptable'].choices = nodelicense_choices

    def clean_subjects_acceptable(self, *args, **kwargs):
        subject_ids = filter(None, self.data['subjects_chosen'].split(', '))
        subjects_selected = [Subject.objects.get(id=ident) for ident in subject_ids]
        rules = get_subject_rules(subjects_selected)
        return rules
