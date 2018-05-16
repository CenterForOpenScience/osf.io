import bleach

from django import forms

from osf.models import CollectionProvider
from admin.base.utils import get_nodelicense_choices


class CollectionProviderForm(forms.ModelForm):
    licenses_acceptable = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False, choices=get_nodelicense_choices())
    collected_type_choices = forms.CharField(widget=forms.HiddenInput, required=False)
    status_choices = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = CollectionProvider
        exclude = ['primary_identifier_name','primary_collection', 'type', 'allow_commenting', 'advisory_board',
                   'example', 'domain', 'domain_redirect_enabled', 'reviews_comments_anonymous',
                   'reviews_comments_private', 'reviews_workflow']

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
