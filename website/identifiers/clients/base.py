# -*- coding: utf-8 -*-
import requests

from framework.exceptions import HTTPError
from website import settings


class AbstractIndentifierClient(object):

    def __init__(self, base_url, prefix):
        self.base_url = base_url
        self.prefix = prefix

    def build_metadata(self, object):
        """ Build the metadata object used to register the object
        with the specified client"""
        raise NotImplementedError()

    def build_doi(self, object):
        """Method this client uses to build a DOI"""
        return settings.DOI_FORMAT.format(prefix=self.prefix, guid=object._id)

    def _make_request(self, method, url, **kwargs):
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', None)
        response = requests.request(method, url, **kwargs)
        if expects and response.status_code not in expects:
            raise throws if throws else HTTPError(response.status_code, message=response.content)

        return response

    def create_identifier(self, metadata, doi):
        """ Make a request to register the given identifier
        with the client"""
        raise NotImplementedError()

    def change_status_identifier(self, status, identifier):
        """Register a change in metadata with the given client
        """
        raise NotImplementedError()
