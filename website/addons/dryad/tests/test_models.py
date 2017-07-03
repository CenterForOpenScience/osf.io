from nose.tools import assert_equals, assert_false, assert_true, assert_equal
import httpretty
from framework.auth import Auth

from website.addons.dryad.tests.utils import (DryadTestCase, AuthUserFactory,
                                              ProjectFactory,
                                              dryad_meta_url)


class DryadTestModel(DryadTestCase):

    def setUp(self):
        super(DryadTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('dryad', auth=Auth(self.user))
        #self.project.creator.add_addon('dryad', auth=Auth(self.user))
        self.node_settings = self.project.get_addon('dryad')
        #self.user_settings = self.project.creator.get_addon('dryad')
        #self.user_settings.save()
        #self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

    @httpretty.activate
    def test_doi_creation_order(self):
        httpretty.register_uri(
            httpretty.GET,
            dryad_meta_url,
            status=200
        )

        assert_equals(self.node_settings.dryad_package_doi, None)
        assert_false(self.node_settings.dryad_package_doi == '10.5061/dryad.1850')
        num_logs = len(self.project.logs)
        self.node_settings.set_doi('10.5061/dryad.1850', 'My Fake Package',
                                   auth=Auth(self.user))
        assert_false(self.node_settings.dryad_package_doi == '')
        assert_equals(self.node_settings.dryad_package_doi,
                      '10.5061/dryad.1850')
        num_logs += 1
        assert_equals(len(self.project.logs), num_logs)
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dryad_doi_set')

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.dryad_package_doi is None)
