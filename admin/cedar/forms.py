from django.forms import ModelForm, CharField, JSONField

from osf.models import CedarMetadataTemplate


class CedarMetadataTemplateForm(ModelForm):
    schema_name = CharField(disabled=True, max_length=200)
    cedar_id = CharField(disabled=True, max_length=200)
    template_version = CharField(disabled=True, max_length=200)
    template = JSONField(disabled=True)

    class Meta:
        model = CedarMetadataTemplate
        fields = [
            "schema_name",
            "cedar_id",
            "template_version",
            "template",
            "active",
        ]
