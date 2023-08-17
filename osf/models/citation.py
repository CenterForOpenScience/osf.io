from django.db import models
from django.utils import timezone
from .base import BaseModel
from osf.utils.fields import NonNaiveDateTimeField


class CitationStyle(BaseModel):
    """Persistent representation of a CSL style.

    These are parsed from .csl files, so that metadata fields can be indexed.
    """

    primary_identifier_name = '_id'

    # The name of the citation file, sans extension
    _id = models.CharField(max_length=255, db_index=True)

    # The full title of the style
    title = models.CharField(max_length=255)

    # Datetime the file was last parsed
    date_parsed = NonNaiveDateTimeField(default=timezone.now)

    short_title = models.CharField(max_length=2048, null=True, blank=True)
    summary = models.CharField(max_length=4200, null=True, blank=True)  # longest value was 3,812 8/23/2016
    has_bibliography = models.BooleanField(default=False)
    parent_style = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['_id']

    def to_json(self):
        return {
            'id': self._id,
            'title': self.title,
            'short_title': self.short_title,
            'summary': self.summary,
            'has_bibliography': self.has_bibliography,
            'parent_style': self.parent_style
        }

    @property
    def has_parent_style(self):
        return self.parent_style is not None
