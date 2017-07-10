# -*- coding: utf-8 -*-

from django.db import models

from addons.base.models import BaseCitationsNodeSettings
from addons.dryad.provider import DryadProvider
from addons.dryad.serializer import DryadSerializer
from website.project.model import validate_doi


class NodeSettings(BaseCitationsNodeSettings):
    """
        A Dryad node is a collection of packages. Each package is specified by a DOI, and the title is saved automatically
    """
    provider_name = 'dryad'
    oauth_provider = DryadProvider
    serializer = DryadSerializer
    dryad_package_doi = models.CharField(max_length=128, blank=True, null=True, validators=[validate_doi])
    has_auth = True
    complete = True
    list_id = None

    _api = None

    @property
    def api(self):
        if not self._api:
            self._api = DryadProvider()
        return self._api

    def delete(self, **kwargs):
        self.dryad_package_doi = None
        super(NodeSettings, self).delete()

    def serialize_waterbutler_settings(self):
        return {'doi': self.dryad_package_doi}

    def set_doi(self, doi, title, auth):
        if self.api.check_dryad_doi(doi) and validate_doi(doi):
            self.dryad_package_doi = doi
            self.owner.add_log(action='dryad_doi_set', auth=auth,
                               params={'project': self.owner.parent_id,
                                       'node': self.owner._id,
                                       'folder': doi
                                       })
            return True
        return False
