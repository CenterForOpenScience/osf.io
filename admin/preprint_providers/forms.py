from django.forms import ModelForm, CheckboxSelectMultiple, MultipleChoiceField, HiddenInput, CharField

from osf.models import PreprintProvider, Subject
from admin.base.utils import get_subject_rules, get_toplevel_subjects, get_nodelicense_choices


class PreprintProviderForm(ModelForm):
    toplevel_subjects = MultipleChoiceField(choices=get_toplevel_subjects(), widget=CheckboxSelectMultiple())
    subjects_chosen = CharField(widget=HiddenInput())

    class Meta:
        model = PreprintProvider

        exclude = ['modm_model_path', 'modm_query', '_id']

        widgets = {
            'licenses_acceptable': CheckboxSelectMultiple(choices=get_nodelicense_choices()),
            'subjects_acceptable': HiddenInput(),
        }

    def clean_subjects_acceptable(self, *args, **kwargs):
        subject_ids = filter(None, self.data['subjects_chosen'].split(', '))
        subjects_selected = [Subject.objects.get(id=ident) for ident in subject_ids]
        rules = get_subject_rules(subjects_selected)
        return rules
