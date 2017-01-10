from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


class Identifier(ObjectIDMixin, BaseModel):
    """A persistent identifier model for DOIs, ARKs, and the like."""

    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.identifiers.model.Identifier'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION

    # object to which the identifier points
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    referent = GenericForeignKey()
    # category: e.g. 'ark', 'doi'
    category = models.CharField(max_length=10)  # longest was 3, 8/19/2016
    # value: e.g. 'FK424601'
    value = models.CharField(max_length=50)  # longest was 21, 8/19/2016

    class Meta:
        unique_together = ('object_id', 'content_type', 'category')


class IdentifierMixin(models.Model):
    """Model mixin that adds methods for getting and setting Identifier objects
    for model objects.
    """

    def get_identifier(self, category):
        """Returns None of no identifier matches"""
        return Identifier.objects.filter(nodes=self, category=category).first()

    def get_identifier_value(self, category):
        identifier = self.get_identifier(category)
        return identifier.value if identifier else None

    def set_identifier_value(self, category, value):
        identifier, created = Identifier.objects.get_or_create(object_id=self.pk,
                                                               content_type=ContentType.objects.get_for_model(self),
                                                               category=category,
                                                               defaults=dict(value=value))
        if not created:
            identifier.value = value
            identifier.save()

    class Meta:
        abstract = True
