import bleach

from django import forms

from osf.models import RegistrationProvider, Subject
from admin.base.utils import (
    get_nodelicense_choices,
    get_defaultlicense_choices,
    validate_slug,
    get_brand_choices,
)


class RegistrationProviderForm(forms.ModelForm):
    _id = forms.SlugField(
        required=True,
        help_text='URL Slug',
        validators=[validate_slug]
    )

    class Meta:
        model = RegistrationProvider
        exclude = [
            'primary_identifier_name',
            'primary_collection',
            'type',
            'advisory_board',
            'example',
            'domain',
            'domain_redirect_enabled',
            'collected_type_choices',
            'status_choices',
            'reviews_comments_private',
            'reviews_comments_anonymous',
        ]

        widgets = {
            'licenses_acceptable': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        nodelicense_choices = get_nodelicense_choices()
        defaultlicense_choices = get_defaultlicense_choices()
        brand_choices = get_brand_choices()
        super(RegistrationProviderForm, self).__init__(*args, **kwargs)
        self.fields['licenses_acceptable'].choices = nodelicense_choices
        self.fields['default_license'].choices = defaultlicense_choices
        self.fields['brand'].choices = brand_choices

    def clean_description(self, *args, **kwargs):
        if not self.data.get('description'):
            return u''
        return bleach.clean(
            self.data.get('description'),
            tags=['a', 'br', 'em', 'p', 'span', 'strong'],
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles=['text-align', 'vertical-align'],
            strip=True
        )

    def clean_footer_links(self, *args, **kwargs):
        if not self.data.get('footer_links'):
            return u''
        return bleach.clean(
            self.data.get('footer_links'),
            tags=['a', 'br', 'div', 'em', 'p', 'span', 'strong'],
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles=['text-align', 'vertical-align'],
            strip=True
        )

class RegistrationProviderCustomTaxonomyForm(forms.Form):
    add_missing = forms.BooleanField(required=False)
    custom_taxonomy_json = forms.CharField(widget=forms.Textarea, initial='{"include": [], "exclude": [], "custom": {}, "merge": {}}', required=False)
    provider_id = forms.IntegerField(widget=forms.HiddenInput())
    include = forms.ChoiceField(choices=[], required=False)
    exclude = forms.ChoiceField(choices=[], required=False)
    custom_name = forms.CharField(required=False)
    custom_parent = forms.CharField(required=False)
    bepress = forms.ChoiceField(choices=[], required=False)

    merge_from = forms.ChoiceField(choices=[], required=False)
    merge_into = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super(RegistrationProviderCustomTaxonomyForm, self).__init__(*args, **kwargs)
        subject_choices = [(x, x) for x in Subject.objects.filter(bepress_subject__isnull=True).values_list('text', flat=True)]
        for name, field in self.fields.items():
            if hasattr(field, 'choices'):
                if field.choices == []:
                    field.choices = subject_choices
