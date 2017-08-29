import bleach

from django.forms import ModelForm, CheckboxSelectMultiple, MultipleChoiceField, HiddenInput, CharField

from osf.models import PreprintProvider, Subject
from admin.base.utils import get_subject_rules, get_toplevel_subjects, get_nodelicense_choices


class PreprintProviderForm(ModelForm):
    toplevel_subjects = MultipleChoiceField(widget=CheckboxSelectMultiple(), required=False)
    subjects_chosen = CharField(widget=HiddenInput(), required=False)

    class Meta:
        model = PreprintProvider

        exclude = ['primary_identifier_name']

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
