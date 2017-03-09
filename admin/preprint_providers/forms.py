from django.forms import ModelForm, SelectMultiple, CheckboxSelectMultiple, Form, MultipleChoiceField, HiddenInput, CharField


from osf.models import PreprintProvider, Subject, NodeLicense


CHOICES = [(sub.id, sub.text) for sub in NodeLicense.objects.all()]


class PreprintProviderForm(ModelForm):
    class Meta:
        model = PreprintProvider

        exclude = ['modm_model_path', 'modm_query', '_id', 'subjects_acceptable']

        widgets = {
            'licenses_acceptable': CheckboxSelectMultiple(choices=CHOICES),
        }


class PreprintProviderSubjectForm(Form):

    def get_toplevel_subjects():
        subjects = Subject.objects.filter(parents__isnull=True)
        return [(sub.id, sub.text) for sub in subjects]

    toplevel_subjects = MultipleChoiceField(choices=get_toplevel_subjects(), widget=CheckboxSelectMultiple())
    subjects_chosen = CharField(widget=HiddenInput())
