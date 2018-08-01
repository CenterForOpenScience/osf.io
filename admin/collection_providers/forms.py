import bleach
import json

from django import forms

from osf.models import CollectionProvider, CollectedGuidMetadata
from admin.base.utils import get_nodelicense_choices


class CollectionProviderForm(forms.ModelForm):
    licenses_acceptable = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False, choices=get_nodelicense_choices())
    collected_type_choices = forms.CharField(widget=forms.HiddenInput, required=False)
    status_choices = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = CollectionProvider
        exclude = ['primary_identifier_name', 'primary_collection', 'type', 'allow_commenting', 'advisory_board',
                   'example', 'domain', 'domain_redirect_enabled', 'reviews_comments_anonymous',
                   'reviews_comments_private', 'reviews_workflow']

    def clean_description(self, *args, **kwargs):
        if not self.data.get('description'):
            return ''
        return bleach.clean(
            self.data.get('description'),
            tags=['a', 'br', 'em', 'p', 'span', 'strong'],
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles=['text-align', 'vertical-align'],
            strip=True
        )

    def clean_footer_links(self, *args, **kwargs):
        if not self.data.get('footer_links'):
            return ''
        return bleach.clean(
            self.data.get('footer_links'),
            tags=['a', 'br', 'div', 'em', 'p', 'span', 'strong'],
            attributes=['class', 'style', 'href', 'title', 'target'],
            styles=['text-align', 'vertical-align'],
            strip=True
        )

    def clean_collected_type_choices(self):
        collection_provider = self.instance
        # if this is to modify an existing CollectionProvider
        if collection_provider.primary_collection:
            type_choices_old = set(collection_provider.primary_collection.collected_type_choices)
            type_choices_new = set(json.loads(self.data.get('collected_type_choices')))
            type_choices_added = type_choices_new - type_choices_old
            type_choices_removed = type_choices_old - type_choices_new
            for item in type_choices_removed:
                if CollectedGuidMetadata.objects.filter(collection=collection_provider.primary_collection,
                                                        collected_type=item).exists():
                    raise forms.ValidationError(
                        'Cannot delete "{}" because it is used as metadata on objects.'.format(item)
                    )
        else:
            # if this is creating a CollectionProvider
            type_choices_added = json.loads(self.data.get('collected_type_choices'))
            type_choices_removed = []

        return {
            'added': type_choices_added,
            'removed': type_choices_removed,
        }

    def clean_status_choices(self):
        collection_provider = self.instance
        # if this is to modify an existing CollectionProvider
        if collection_provider.primary_collection:
            status_choices_old = set(collection_provider.primary_collection.status_choices)
            status_choices_new = set(json.loads(self.data.get('status_choices')))
            status_choices_added = status_choices_new - status_choices_old
            status_choices_removed = status_choices_old - status_choices_new
            for item in status_choices_removed:
                if CollectedGuidMetadata.objects.filter(collection=collection_provider.primary_collection,
                                                        status=item).exists():
                    raise forms.ValidationError(
                        'Cannot delete "{}" because it is used as metadata on objects.'.format(item)
                    )
        else:
            # if this is creating a CollectionProvider
            status_choices_added = json.loads(self.data.get('status_choices'))
            status_choices_removed = []

        return {
            'added': status_choices_added,
            'removed': status_choices_removed,
        }
