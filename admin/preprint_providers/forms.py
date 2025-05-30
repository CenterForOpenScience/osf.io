from django import forms
from django.contrib.auth.models import Group

from framework.utils import sanitize_html
from osf.models import (
    CitationStyle,
    PreprintProvider,
    Subject
)
from admin.base.utils import (get_subject_rules, get_toplevel_subjects,
    get_nodelicense_choices, get_defaultlicense_choices, validate_slug)


class PreprintProviderForm(forms.ModelForm):
    citation_styles = forms.ModelMultipleChoiceField(
        queryset=CitationStyle.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False
    )

    toplevel_subjects = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(), required=False)
    subjects_chosen = forms.CharField(widget=forms.HiddenInput(), required=False)
    _id = forms.SlugField(
        required=True,
        help_text='URL Slug',
        validators=[validate_slug]
    )

    advertise_on_discover_page = forms.BooleanField(required=False, label='Advertise on Discover Page', initial=True)

    class Meta:
        model = PreprintProvider

        exclude = ['primary_identifier_name', 'primary_collection', 'type']

        widgets = {
            'licenses_acceptable': forms.CheckboxSelectMultiple(),
            'subjects_acceptable': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        toplevel_choices = get_toplevel_subjects()
        nodelicense_choices = get_nodelicense_choices()
        defaultlicense_choices = get_defaultlicense_choices()
        super().__init__(*args, **kwargs)
        self.fields['toplevel_subjects'].choices = toplevel_choices
        self.fields['licenses_acceptable'].choices = nodelicense_choices
        self.fields['default_license'].choices = defaultlicense_choices

    def clean_subjects_acceptable(self, *args, **kwargs):
        subject_ids = [_f for _f in self.data['subjects_chosen'].split(', ') if _f]
        subjects_selected = Subject.objects.filter(id__in=subject_ids)
        rules = get_subject_rules(subjects_selected)
        return rules

    def clean_advisory_board(self, *args, **kwargs):
        if not self.data.get('advisory_board'):
            return ''
        return sanitize_html(
            self.data.get('advisory_board'),
            tags={'a', 'b', 'br', 'div', 'em', 'h2', 'h3', 'li', 'p', 'strong', 'ul'},
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles={'text-align', 'vertical-align', 'color'},
            strip=True
        )

    def clean_description(self, *args, **kwargs):
        if not self.data.get('description'):
            return ''
        return sanitize_html(
            self.data.get('description'),
            tags={'a', 'br', 'em', 'p', 'span', 'strong'},
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles={'text-align', 'vertical-align', 'color'},
            strip=True
        )

    def clean_footer_links(self, *args, **kwargs):
        if not self.data.get('footer_links'):
            return ''
        return sanitize_html(
            self.data.get('footer_links'),
            tags={'a', 'br', 'div', 'em', 'p', 'span', 'strong'},
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles={'text-align', 'vertical-align', 'color'},
            strip=True
        )


class PreprintProviderCustomTaxonomyForm(forms.Form):
    add_missing = forms.BooleanField(required=False)
    custom_taxonomy_json = forms.CharField(widget=forms.Textarea, initial='{"include": [], "exclude": [], "custom": {}, "merge": {}}', required=False)
    include = forms.ChoiceField(choices=[], required=False)
    exclude = forms.ChoiceField(choices=[], required=False)
    custom_name = forms.CharField(required=False)
    custom_parent = forms.CharField(required=False)
    bepress = forms.ChoiceField(choices=[], required=False)

    merge_from = forms.ChoiceField(choices=[], required=False)
    merge_into = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        subject_choices = [(x, x) for x in Subject.objects.filter(bepress_subject__isnull=True).values_list('text', flat=True)]
        for name, field in self.fields.items():
            if hasattr(field, 'choices'):
                if field.choices == []:
                    field.choices = subject_choices


class PreprintProviderRegisterModeratorOrAdminForm(forms.Form):
    """ A form that finds an existing OSF User, and grants permissions to that
        user so that they can use the admin app"""

    def __init__(self, *args, provider_groups=None, **kwargs):
        super().__init__(*args, **kwargs)

        provider_groups = provider_groups or Group.objects.none()
        self.fields['group_perms'] = forms.ModelMultipleChoiceField(
            queryset=provider_groups,
            required=False,
            widget=forms.CheckboxSelectMultiple
        )

    user_id = forms.CharField(required=True, max_length=5, min_length=5)
