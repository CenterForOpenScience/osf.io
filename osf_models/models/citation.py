import datetime
from django.db import models
from osf_models.models.base import BaseModel, ObjectIDMixin


class AlternativeCitation(ObjectIDMixin, BaseModel):
    name = models.CharField(max_length=256)
    text = models.CharField(max_length=2048)

    def to_json(self):
        return {
            'id': self._id,
            'name': self.name,
            'text': self.text
        }


class CitationStyle(BaseModel):
    """Persistent representation of a CSL style.

    These are parsed from .csl files, so that metadata fields can be indexed.
    """

    # The name of the citation file, sans extension
    _id = models.CharField(max_length=255, db_index=True)

    # The full title of the style
    title = models.CharField(max_length=255)

    # Datetime the file was last parsed
    date_parsed = models.DateTimeField(default=datetime.datetime.utcnow)

    short_title = models.CharField(max_length=2048)
    summary = models.CharField(max_length=2048)

    def to_json(self):
        return {
            'id': self._id,
            'title': self.title,
            'short_title': self.short_title,
            'summary': self.summary,
        }

