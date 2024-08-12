from django.db import models

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField


class CedarMetadataTemplate(ObjectIDMixin, BaseModel):
    schema_name = models.CharField(max_length=255, default=None)
    cedar_id = models.CharField(max_length=255, default=None)
    template = DateTimeAwareJSONField(default=dict)
    active = models.BooleanField(default=True)
    template_version = models.PositiveIntegerField()

    class Meta:
        unique_together = ("cedar_id", "template_version")

    def __unicode__(self):
        return f"(name=[{self.schema_name}], version=[{self.template_version}], id=[{self.cedar_id}])"

    def get_semantic_iri(self):
        return self.cedar_id

    def is_active(self):
        return self.active


class CedarMetadataRecord(ObjectIDMixin, BaseModel):
    guid = models.ForeignKey(
        "Guid", on_delete=models.CASCADE, related_name="cedar_metadata_records"
    )
    template = models.ForeignKey(
        "CedarMetadataTemplate", on_delete=models.CASCADE
    )
    metadata = DateTimeAwareJSONField(default=dict)
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = ("guid", "template")

    def __unicode__(self):
        return f"(guid=[{self.guid._id}], template=[{self.template._id}])"

    def get_template_semantic_iri(self):
        return self.template.get_semantic_iri()

    def get_template_name(self):
        return self.template.schema_name

    def get_template_version(self):
        return self.template.template_version

    def save(self, *args, **kwargs):
        self.guid.referent.update_search()
        return super().save(*args, **kwargs)
