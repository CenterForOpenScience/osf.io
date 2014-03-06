import nose
from nose.tools import *
from webtest_plus import TestApp

from framework.auth.decorators import Auth
import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from website.addons.dataverse.views.crud import scrape_dataverse

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)

class TestDataverseViewsAuth(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)


        self.project.add_addon('dataverse', auth=self.consolidated_auth)
        self.user.add_addon('dataverse')

        self.user_settings = self.user.get_addon('dataverse')
        self.user_settings.dataverse_username = 'snowman'
        self.user_settings.dataverse_password = 'frosty'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('dataverse')
        self.node_settings.user_settings = self.project.creator.get_addon('s3')
        self.node_settings.dataverse_username = self.user_settings.dataverse_username
        self.node_settings.dataverse_password = self.user_settings.dataverse_password
        self.node_settings.dataverse_number = 1
        self.node_settings.study_hdl = 'DVN/12345'
        self.node_settings.study = 'My Study'
        self.node_settings.user = self.user
        self.node_settings.save()

    def test_unauthorize(self):
        url = self.project.api_url + 'dataverse/unauthorize/'
        res = self.app.post_json(
            url,
            auth=self.user.auth
        )
        self.node_settings.reload()
        assert_false(self.node_settings.dataverse_username)
        assert_false(self.node_settings.dataverse_password)
        assert_equal(self.node_settings.dataverse_number, 0)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user)



def test_scrape_dataverse():
    content = scrape_dataverse(2362170)
    assert_not_in('IQSS', content)
    assert_in('%esp', content)

if __name__=='__main__':
    nose.run()