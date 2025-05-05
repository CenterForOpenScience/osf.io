from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from osf.exceptions import (
    IdentifierHasReferencesError,
    NoSuchPIDValidatorError,
)
from osf.metadata.rdfutils import DOI
from .base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils import identifiers as identifier_utils


class Identifier(ObjectIDMixin, BaseModel):
    """A persistent identifier model for DOIs, ARKs, and the like."""

    # object to which the identifier points
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    referent = GenericForeignKey()
    # category: e.g. 'ark', 'doi'
    category = models.CharField(max_length=20)  # longest was 3, 8/19/2016
    # value: e.g. 'FK424601'
    value = models.CharField(max_length=50)  # longest was 21, 8/19/2016
    deleted = NonNaiveDateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('object_id', 'content_type', 'category')

    def remove(self, save=True):
        """Mark an identifier as deleted, which excludes it from being returned in get_identifier"""
        self.deleted = timezone.now()
        if save:
            self.save()

    def delete(self):
        '''Used to delete an orphaned Identifier (distinct from setting `deleted`)'''
        if self.object_id or self.artifact_metadata.filter(deleted__isnull=True).exists():
            raise IdentifierHasReferencesError
        super().delete()

    def validate_identifier_value(self):
        # We created the PID, so assume valid
        if self.object_id is not None:
            return True

        # If we don't know how to validate a PID, assume it's fine
        try:
            validator = identifier_utils.PIDValidator.for_identifier_category(self.category)
        except NoSuchPIDValidatorError:
            return True

        # Let the caller decide what to do with any validation errors
        return validator.validate(self.value)

    def as_semantic_iri(self) -> str:
        if self.category == 'doi':
            return DOI[self.value]
        raise ValueError(f'unsure how to iri with category "{self.category}"')


class IdentifierMixin(models.Model):
    """Model mixin that adds methods for getting and setting Identifier objects
    for model objects.
    """

    @property
    def should_request_identifiers(self):
        """Determines if a identifier should be requested, Bool.
        """
        raise NotImplementedError()

    def get_doi_client(self):
        """Return a BaseIdentifierClient if proper
        settings are configured, else return None
        """
        raise NotImplementedError()

    def request_identifier(self, category):
        client = self.get_doi_client()
        if client:
            return client.create_identifier(self, category)

    def request_identifier_update(self, category, create=False):
        '''Noop if no existing identifier value for the category.'''

        # if not self.get_identifier_value(category) and not create:
        #     return

        client = self.get_doi_client()
        if client:
            return client.update_identifier(self, category)

    def all_identifiers(self):
        return Identifier.objects.filter(
            object_id=self.id,
            content_type=ContentType.objects.get_for_model(self),
            deleted__isnull=True,
        )

    def get_identifier(self, category):
        """Returns None of no identifier matches"""
        found_identifier = self.all_identifiers().filter(category=category).first()
        if category == 'doi' and not found_identifier:
            found_identifier = self.all_identifiers().filter(category='legacy_doi').first()
        return found_identifier

    def get_identifier_value(self, category):
        identifier = self.get_identifier(category)
        return identifier.value if identifier else None

    def set_identifier_value(self, category, value=None):
        defaults = {'value': value} if value is not None else {}
        identifier, created = Identifier.objects.get_or_create(object_id=self.pk,
                                                               content_type=ContentType.objects.get_for_model(self),
                                                               category=category,
                                                               defaults=defaults)
        if value and not created:
            identifier.value = value
            identifier.save()

    def get_semantic_iris(self):
        try:  # since this is a mixin, don't assume osf.models.BaseModel
            _get_super_iris = super().get_semantic_iris
        except AttributeError:
            pass
        else:
            yield from _get_super_iris()
        # yield each identifier as iri
        for _identifier in self.all_identifiers():
            try:
                yield _identifier.as_semantic_iri()
            except ValueError:
                pass

    class Meta:
        abstract = True
