from django.forms import ModelForm, CharField, JSONField, BooleanField

from osf.models import CedarMetadataTemplate


class CedarMetadataTemplateForm(ModelForm):
    schema_name = CharField(
        disabled=True,
        max_length=200
    )
    cedar_id = CharField(
        disabled=True,
        max_length=200
    )
    template_version = CharField(
        disabled=True,
        max_length=200
    )
    template = JSONField(
        disabled=True
    )
    is_for_collections = BooleanField(label='For collections only:', required=False)

    class Meta:
        model = CedarMetadataTemplate
        fields = ['schema_name', 'cedar_id', 'template_version', 'template', 'is_for_collections', 'active', 'should_index_for_search']
