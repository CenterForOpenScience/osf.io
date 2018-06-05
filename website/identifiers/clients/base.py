# -*- coding: utf-8 -*-

class AbstractIdentifierClient(object):

    def __init__(self, base_url, prefix):
        self.base_url = base_url
        self.prefix = prefix

    def build_metadata(self, object):
        """ Build the metadata object used to register the object
        with the specified client"""
        raise NotImplementedError()

    def build_doi(self, object):
        """Method this client uses to build a DOI
        """
        raise NotImplementedError()

    def create_identifier(self, metadata, doi):
        """ Make a request to register the given identifier
        with the client"""
        raise NotImplementedError()

    def change_status_identifier(self, status, identifier):
        """Register a change in metadata with the given client
        """
        raise NotImplementedError()
