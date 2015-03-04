# -*- coding: utf-8 -*-

import datetime

from modularodm import fields

from framework.mongo import StoredObject


class CitationStyle(StoredObject):
    """Persistent representation of a CSL style.

    These are parsed from .csl files, so that metadata fields can be indexed.
    """

    # The name of the citation file, sans extension
    _id = fields.StringField(primary=True)

    # The full title of the style
    title = fields.StringField(required=True)

    # Datetime the file was last parsed
    date_parsed = fields.DateTimeField(default=datetime.datetime.utcnow,
                                       required=True)

    short_title = fields.StringField(required=False)
    summary = fields.StringField(required=False)

    def to_json(self):
        return {
            'id': self._id,
            'title': self.title,
            'short_title': self.short_title,
            'summary': self.summary,
        }
