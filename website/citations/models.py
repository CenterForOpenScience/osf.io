import datetime
from collections import Iterable

from modularodm import fields

from framework.mongo import StoredObject
from website import citations


class Citation(dict):
    @property
    def json(self):
        """Json-encodable dict conforming to the CSL-data schema"""
        return self



class CitationList(object):

    def __init__(self,
                 name=None,
                 provider_list_id=None,
                 provider_account_id=None,
                 citations=None):
        self.name = name
        self.provider_list_id = provider_list_id
        self.provider_account_id = provider_account_id
        if citations is not None:
            self.citations = citations

    def __repr__(self):
        return '<CitationList: {}>'.format(self.name or '[anonymous]')

    __get_citations = None
    __citations = None

    @property
    def _get_citations(self):
        """Unbound callable that returns a list of Citation instances

        This property must be assigned with a CitationList is instantiated IF
        self._citations is not assigned. If self._citations is assigned, this
        need not be assigned because it will not be accessed.

        :return: iterable(Citation)
        """
        if self.__get_citations is None:
            raise NotImplementedError()
        return self.__get_citations

    @_get_citations.setter
    def _get_citations(self, value):
        self.__get_citations = value

    @property
    def citations(self):
        """Iterable of citations belonging to this CitationList

        :return: iterable(Citation)
        """
        if self.__citations is None:
            self.__citations = self._get_citations()

        return self.__citations

    @citations.setter
    def citations(self, val):
        if callable(val):
            self._get_citations = val
        elif isinstance(val, Iterable):
            self.__citations = val
        else:
            raise ValueError("must be iterable or callable")

    @property
    def json(self):
        """JSON-formatted string for instance, not including citations"""
        return {
            'name': self.name,
            'provider_list_id': self.provider_list_id,
            'provider_account_id': self.provider_account_id,
        }

    def render(self, style):
        rv = self.json
        rv['citations'] = list(citations.render_iterable(self.citations, style))
        return rv


class CitationStyle(StoredObject):

    # The name of the citation file, sans extension
    _id = fields.StringField(primary=True)

    # The full title of the style
    title = fields.StringField(required=True)

    # Datetime the file was last parsed
    date_parsed = fields.DateTimeField(default=datetime.datetime.utcnow,
                                       required=True)

    short_title = fields.StringField()
    summary = fields.StringField()

    def to_json(self):
        return {
            'id': self._id,
            'title': self.title,
            'short_title': self.short_title,
            'summary': self.summary,
        }