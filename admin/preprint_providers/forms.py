import bleach

from django import forms

from osf.models import PreprintProvider, Subject
from admin.base.utils import get_subject_rules, get_toplevel_subjects, get_nodelicense_choices


class PreprintProviderForm(forms.ModelForm):
    toplevel_subjects = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(), required=False)
    subjects_chosen = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = PreprintProvider

        exclude = ['primary_identifier_name']

        widgets = {
            'licenses_acceptable': forms.CheckboxSelectMultiple(),
            'subjects_acceptable': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        toplevel_choices = get_toplevel_subjects()
        nodelicense_choices = get_nodelicense_choices()
        super(PreprintProviderForm, self).__init__(*args, **kwargs)
        self.fields['toplevel_subjects'].choices = toplevel_choices
        self.fields['licenses_acceptable'].choices = nodelicense_choices

    def clean_subjects_acceptable(self, *args, **kwargs):
        subject_ids = filter(None, self.data['subjects_chosen'].split(', '))
        subjects_selected = Subject.objects.filter(id__in=subject_ids)
        rules = get_subject_rules(subjects_selected)
        return rules

    def clean_advisory_board(self, *args, **kwargs):
        return bleach.clean(
            self.data.get('advisory_board'),
            tags=['a', 'b', 'br', 'div', 'em', 'h2', 'h3', 'li', 'p', 'strong', 'ul'],
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles=['text-align', 'vertical-align'],
            strip=True
        )

    def clean_description(self, *args, **kwargs):
        return bleach.clean(
            self.data.get('description'),
            tags=['a', 'br', 'em', 'p', 'span', 'strong'],
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles=['text-align', 'vertical-align'],
            strip=True
        )

    def clean_footer_links(self, *args, **kwargs):
        return bleach.clean(
            self.data.get('footer_links'),
            tags=['a', 'br', 'div', 'em', 'p', 'span', 'strong'],
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles=['text-align', 'vertical-align'],
            strip=True
        )


class PreprintProviderCustomTaxonomyForm(forms.Form):
    custom_taxonomy_json = forms.CharField(widget=forms.Textarea, initial='{"include": [], "exclude": [], "custom": {}}', required=False)
    provider_id = forms.IntegerField(widget=forms.HiddenInput())
    include = forms.ChoiceField(choices=[], required=False)
    exclude = forms.ChoiceField(choices=[], required=False)
    custom_name = forms.CharField(required=False)
    custom_parent = forms.CharField(required=False)
    bepress = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super(PreprintProviderCustomTaxonomyForm, self).__init__(*args, **kwargs)
        subject_choices = [(x, x) for x in Subject.objects.all().values_list('text', flat=True)]
        for name, field in self.fields.iteritems():
            if hasattr(field, 'choices'):
                if field.choices == []:
                    field.choices = subject_choices
