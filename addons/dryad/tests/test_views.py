#!/usr/bin/env python
# encoding: utf-8
import httpretty
from furl import furl
import pytest

from nose.tools import assert_true, assert_false, assert_equal

from addons.dryad.settings import DRYAD_BASE_URL
from addons.dryad.tests.utils import DryadTestCase, dryad_meta_url, response_dict
from framework.auth import Auth
from osf_tests.factories import AuthUserFactory, ProjectFactory

pytestmark = pytest.mark.django_db


class TestJSONViews(DryadTestCase):
    """
        TODO: Add in unit tests for browse and search calls. This is a
        bit challenging as there are A LOT of dryad API calls for these two.
        This might call for a refactor of the knockout code
    """

    def setUp(self):
        super(DryadTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('dryad', auth=Auth(self.user))
        self.user.save()
        self.node_settings = self.project.get_addon('dryad')
        self.node_settings.save()

    @httpretty.activate
    def test_validate_doi(self):
        httpretty.register_uri(
            httpretty.GET,
            dryad_meta_url,
            status=200
        )

        url = self.project.api_url_for('dryad_validate_doi')
        resp = self.app.get(url, auth=self.user.auth, params={'doi': '10.5061/dryad.1850'})
        assert_true(resp.json)

        dryad_nonmetadata_path = furl(DRYAD_BASE_URL)
        dryad_nonmetadata_path.path.segments = ['mn', 'object', 'doi:NOTADOI']
        dryad_nonmeta_url = dryad_nonmetadata_path.url

        httpretty.register_uri(
            httpretty.GET,
            dryad_nonmeta_url,
            status=404
        )

        resp = self.app.get(url, auth=self.user.auth, params={'doi': 'NOTADOI'})
        assert_false(resp.json)

    @httpretty.activate
    def test_dryad_set_doi(self):
        httpretty.register_uri(
            httpretty.GET,
            dryad_meta_url,
            responses=[httpretty.Response(body=response_dict[dryad_meta_url],
                       status=200)]
        )

        url = self.project.api_url_for('dryad_set_doi')

        doi = '10.5061/dryad.1850'
        self.app.put_json(url, auth=self.user.auth, params={'doi': doi})
        self.node_settings.reload()
        assert_equal(self.node_settings.dryad_package_doi, doi)
        assert self.node_settings.owner.logs.latest().action == 'dryad_doi_set'

    @httpretty.activate
    def test_dryad_get_current_metadata(self):

        httpretty.register_uri(
            httpretty.GET,
            dryad_meta_url,
            responses=[httpretty.Response(body=response_dict[dryad_meta_url],
                       status=200),
                       ]
        )
        url = self.project.api_url_for('dryad_get_current_metadata')
        meta_resp = self.app.get(url, auth=self.user.auth, params={'doi': '10.5061/dryad.1850'})
        assert_equal(meta_resp.json['doi'], '10.5061/dryad.1850')
