#!/usr/bin/env python
# encoding: utf-8
import httpretty
from furl import furl

from nose.tools import assert_true, assert_false, assert_equal

from framework.auth import Auth

from nose.tools import *  # noqa

from website.addons.dryad.settings import DRYAD_BASE_URL
from website.addons.dryad.tests.utils import (DryadTestCase, AuthUserFactory,
                                              ProjectFactory, dryad_meta_url,
                                              response_dict)


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
        #self.project.creator.add_addon('dryad', auth=Auth(self.user))
        self.user.save()
        self.node_settings = self.project.get_addon('dryad')
        #self.user_settings = self.project.creator.get_addon('dryad', auth=Auth(self.user))
        #self.user_settings.save()
        #self.node_settings.user_settings = self.user_settings
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
        settings = self.node_settings
        settings.reload()
        assert_equal(settings.dryad_package_doi, doi)

    @httpretty.activate
    def test_dryad_get_current_metadata(self):

        httpretty.register_uri(
            httpretty.GET,
            dryad_meta_url,
            responses=[httpretty.Response(body='Response to Set DOI', status=200),
                       httpretty.Response(body=response_dict[dryad_meta_url],
                       status=200),
                       ]
        )
        settings = self.node_settings
        assert_true(settings.set_doi('10.5061/dryad.1850', 'My Title',
                    auth=Auth(self.user)))
        assert_equal(settings.dryad_package_doi, '10.5061/dryad.1850')
        settings.save()
        url = self.project.api_url_for('dryad_get_current_metadata')
        meta_resp = self.app.get(url, auth=self.user.auth)
        assert_equal(meta_resp.json['doi'], '10.5061/dryad.1850')
