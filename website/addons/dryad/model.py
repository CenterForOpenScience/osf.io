# -*- coding: utf-8 -*-
from modularodm import fields
from website.project.model import validate_doi
from website.addons.dryad.provider import DryadProvider
from website.addons.dryad.serializer import DryadSerializer
from website.citations.models import AddonCitationsNodeSettings


class DryadNodeSettings(AddonCitationsNodeSettings):
    """
        A Dryad node is a collection of packages. Each package is specified by a DOI, and the title is saved automatically
    """
    provider_name = 'dryad'
    oauth_provider = DryadProvider
    serializer = DryadSerializer
    dryad_package_doi = fields.StringField()
    has_auth = True
    complete = True

    _api = None

    @property
    def api(self):
        if not self._api:
            self._api = DryadProvider()
        return self._api

    def delete(self, **kwargs):
        self.dryad_package_doi = None
        super(DryadNodeSettings, self).delete()

    @property
    def folder_id(self):
        return self.dryad_package_doi

    @property
    def folder_name(self):
        return self.dryad_package_doi

    @property
    def fetch_folder_name(self):
        return self.dryad_package_doi

    @property
    def configured(self):
        return self.dryad_package_doi is not None

    def serialize_waterbutler_credentials(self):
        return {'storage': {}}

    def serialize_waterbutler_settings(self):
        return {'doi': self.dryad_package_doi}

    def create_waterbutler_log(self, auth, action, metadata):
        path = metadata['path']
        self.owner.add_log(
            'dryad_{}'.format(action),
            auth=auth,
            params={'project': self.owner.parent_id,
                    'node': self.owner._id,
                    'path': path,
                    'folder': self.dryad_package_doi
                    })

    def set_doi(self, doi, title, auth):
        if self.api.check_dryad_doi(doi) and validate_doi(doi):
            self.dryad_package_doi = doi
            self.owner.add_log(action='dryad_doi_set', auth=auth,
                               params={'project': self.owner.parent_id,
                                       'node': self.owner._id,
                                       'folder': self.dryad_package_doi
                                       })
            return True
        return False
