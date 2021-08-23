import bleach
import json

from django import forms

from osf.models import CollectionProvider, CollectionSubmission
from admin.base.utils import get_nodelicense_choices, get_defaultlicense_choices, validate_slug


class CollectionProviderForm(forms.ModelForm):
    collected_type_choices = forms.CharField(widget=forms.HiddenInput(), required=False)
    status_choices = forms.CharField(widget=forms.HiddenInput(), required=False)
    volume_choices = forms.CharField(widget=forms.HiddenInput(), required=False)
    issue_choices = forms.CharField(widget=forms.HiddenInput(), required=False)
    program_area_choices = forms.CharField(widget=forms.HiddenInput(), required=False)
    school_type_choices = forms.CharField(widget=forms.HiddenInput(), required=False)
    study_design_choices = forms.CharField(widget=forms.HiddenInput(), required=False)
    _id = forms.SlugField(
        required=True,
        help_text='URL Slug',
        validators=[validate_slug]
    )

    class Meta:
        model = CollectionProvider
        exclude = ['primary_identifier_name', 'primary_collection', 'type', 'allow_commenting', 'advisory_board',
                   'example', 'domain', 'domain_redirect_enabled', 'reviews_comments_anonymous',
                   'reviews_comments_private', 'reviews_workflow']

        widgets = {
            'licenses_acceptable': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        nodelicense_choices = get_nodelicense_choices()
        defaultlicense_choices = get_defaultlicense_choices()
        super(CollectionProviderForm, self).__init__(*args, **kwargs)
        self.fields['licenses_acceptable'].choices = nodelicense_choices
        self.fields['default_license'].choices = defaultlicense_choices

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

    def clean_collected_type_choices(self):
        collection_provider = self.instance
        # if this is to modify an existing CollectionProvider
        if collection_provider.primary_collection:
            type_choices_old = set([c.strip(' ') for c in collection_provider.primary_collection.collected_type_choices])
            type_choices_new = set([c.strip(' ') for c in json.loads(self.data.get('collected_type_choices'))])
            type_choices_added = type_choices_new - type_choices_old
            type_choices_removed = type_choices_old - type_choices_new
            for item in type_choices_removed:
                if CollectionSubmission.objects.filter(collection=collection_provider.primary_collection,
                                                        collected_type=item).exists():
                    raise forms.ValidationError(
                        'Cannot delete "{}" because it is used as metadata on objects.'.format(item)
                    )
        else:
            # if this is creating a CollectionProvider
            type_choices_added = []
            type_choices_removed = []
            choices = self.data.get('collected_type_choices')
            if choices:
                type_choices_added = json.loads(choices)

        return {
            'added': type_choices_added,
            'removed': type_choices_removed,
        }

    def clean_status_choices(self):
        collection_provider = self.instance
        # if this is to modify an existing CollectionProvider
        if collection_provider.primary_collection:
            status_choices_old = set([c.strip(' ') for c in collection_provider.primary_collection.status_choices])
            status_choices_new = set([c.strip(' ') for c in json.loads(self.data.get('status_choices'))])
            status_choices_added = status_choices_new - status_choices_old
            status_choices_removed = status_choices_old - status_choices_new
            for item in status_choices_removed:
                if CollectionSubmission.objects.filter(collection=collection_provider.primary_collection,
                                                        status=item).exists():
                    raise forms.ValidationError(
                        'Cannot delete "{}" because it is used as metadata on objects.'.format(item)
                    )
        else:
            # if this is creating a CollectionProvider
            status_choices_added = []
            status_choices_removed = []
            choices = self.data.get('status_choices')
            if choices:
                status_choices_added = json.loads(choices)

        return {
            'added': status_choices_added,
            'removed': status_choices_removed,
        }

    def clean_volume_choices(self):
        collection_provider = self.instance
        # if this is to modify an existing CollectionProvider
        if collection_provider.primary_collection:
            volume_choices_old = set([c.strip(' ') for c in collection_provider.primary_collection.volume_choices])
            volume_choices_new = set([c.strip(' ') for c in json.loads(self.data.get('volume_choices'))])
            volume_choices_added = volume_choices_new - volume_choices_old
            volume_choices_removed = volume_choices_old - volume_choices_new
            for item in volume_choices_removed:
                if CollectionSubmission.objects.filter(collection=collection_provider.primary_collection,
                                                        volume=item).exists():
                    raise forms.ValidationError(
                        'Cannot delete "{}" because it is used as metadata on objects.'.format(item)
                    )
        else:
            # if this is creating a CollectionProvider
            volume_choices_added = []
            volume_choices_removed = []
            choices = self.data.get('volume_choices')
            if choices:
                volume_choices_added = json.loads(choices)

        return {
            'added': volume_choices_added,
            'removed': volume_choices_removed,
        }

    def clean_issue_choices(self):
        collection_provider = self.instance
        # if this is to modify an existing CollectionProvider
        if collection_provider.primary_collection:
            issue_choices_old = set([c.strip(' ') for c in collection_provider.primary_collection.issue_choices])
            issue_choices_new = set([c.strip(' ') for c in json.loads(self.data.get('issue_choices'))])
            issue_choices_added = issue_choices_new - issue_choices_old
            issue_choices_removed = issue_choices_old - issue_choices_new
            for item in issue_choices_removed:
                if CollectionSubmission.objects.filter(collection=collection_provider.primary_collection,
                                                        issue=item).exists():
                    raise forms.ValidationError(
                        'Cannot delete "{}" because it is used as metadata on objects.'.format(item)
                    )
        else:
            # if this is creating a CollectionProvider
            issue_choices_added = []
            issue_choices_removed = []
            choices = self.data.get('issue_choices')
            if choices:
                issue_choices_added = json.loads(choices)

        return {
            'added': issue_choices_added,
            'removed': issue_choices_removed,
        }

    def clean_program_area_choices(self):
        collection_provider = self.instance
        # if this is to modify an existing CollectionProvider
        if collection_provider.primary_collection:
            program_area_choices_old = set([c.strip(' ') for c in collection_provider.primary_collection.program_area_choices])
            program_area_choices_new = set([c.strip(' ') for c in json.loads(self.data.get('program_area_choices'))])
            program_area_choices_added = program_area_choices_new - program_area_choices_old
            program_area_choices_removed = program_area_choices_old - program_area_choices_new
            for item in program_area_choices_removed:
                if CollectionSubmission.objects.filter(collection=collection_provider.primary_collection,
                                                        program_area=item).exists():
                    raise forms.ValidationError(
                        'Cannot delete "{}" because it is used as metadata on objects.'.format(item)
                    )
        else:
            # if this is creating a CollectionProvider
            program_area_choices_added = []
            program_area_choices_removed = []
            choices = self.data.get('program_area_choices')
            if choices:
                program_area_choices_added = json.loads(choices)

        return {
            'added': program_area_choices_added,
            'removed': program_area_choices_removed,
        }

    def clean_school_type_choices(self):
        collection_provider = self.instance
        primary_collection = collection_provider.primary_collection
        if primary_collection:  # Modifying an existing CollectionProvider
            old_choices = {c.strip(' ') for c in primary_collection.school_type_choices}
            updated_choices = {c.strip(' ') for c in json.loads(self.data.get('school_type_choices'))}
            added_choices = updated_choices - old_choices
            removed_choices = old_choices - updated_choices
            active_removed_choices = set(
                primary_collection.collectionsubmission_set.filter(
                    school_type__in=removed_choices
                ).values_list('school_type', flat=True)
            )
            if active_removed_choices:
                raise forms.ValidationError(
                    'Cannot remove the following choices for "school_type", as they are '
                    f'currently in use: {active_removed_choices}'
                )
        else:  # Creating a new CollectionProvider
            added_choices = set()
            removed_choices = set()
            choices = self.data.get('school_type_choices')
            if choices:
                added_choices = json.loads(choices)
        return {'added': added_choices, 'removed': removed_choices}

    def clean_study_design_choices(self):
        collection_provider = self.instance
        primary_collection = collection_provider.primary_collection
        if primary_collection:  # Modifying an existing CollectionProvider
            old_choices = {c.strip(' ') for c in primary_collection.study_design_choices}
            updated_choices = {c.strip(' ') for c in json.loads(self.data.get('study_design_choices'))}
            added_choices = updated_choices - old_choices
            removed_choices = old_choices - updated_choices

            active_removed_choices = set(
                primary_collection.collectionsubmission_set.filter(
                    study_design__in=removed_choices
                ).values_list('school_type', flat=True)
            )
            if active_removed_choices:
                raise forms.ValidationError(
                    'Cannot remove the following choices for "study_design", as they are '
                    f'currently in use: {active_removed_choices}'
                )
        else:  # Creating a new CollectionProvider
            added_choices = set()
            removed_choices = set()
            choices = self.data.get('study_design_choices')
            if choices:
                added_choices = json.loads(choices)
        return {'added': added_choices, 'removed': removed_choices}
