# -*- coding: utf-8 -*-

class AbstractIdentifierClient(object):

    def build_metadata(self, object):
        """ Build the metadata object used to register the object
        with the specified client"""
        raise NotImplementedError()

    def build_doi(self, object):
        """Method this client uses to build a DOI
        """
        raise NotImplementedError()

    def create_identifier(self, object, status='public'):
        """ Make a request to register the given identifier
        with the client"""
        raise NotImplementedError()

    def update_identifier(self, object):
        """Register a change in metadata with the given client
        """
        raise NotImplementedError()
