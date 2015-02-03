import datetime

from modularodm import fields

from framework.mongo import StoredObject


class CitationStyle(StoredObject):

    # Required Fields

    # The name of the citation file, sans extension
    _id = fields.StringField(primary=True)

    # The full title of the style
    title = fields.StringField()

    # Datetime the file was last parsed
    parsed = fields.DateTimeField(default=datetime.datetime.utcnow)

    # Optional Fields

    short_title = fields.StringField()
    summary = fields.StringField()

    def to_json(self):
        return {
            'id': self._id,
            'title': self.title,
            'short_title': self.short_title,
            'summary': self.summary,
        }