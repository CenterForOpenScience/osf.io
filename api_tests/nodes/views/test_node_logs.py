import urlparse

from nose.tools import *  # flake8: noqa
from dateutil.parser import parse as parse_date

from framework.auth.core import Auth
from website.models import NodeLog
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, assert_datetime_equal
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)
import datetime


API_LATEST = 0
API_FIRST = -1
OSF_LATEST = -1
OSF_FIRST = 0


class TestNodeLogList(ApiTestCase):
    def setUp(self):
        super(TestNodeLogList, self).setUp()
        self.user = AuthUserFactory()
        self.contrib = AuthUserFactory()
        self.creator = AuthUserFactory()
        self.user_auth = Auth(self.user)
        self.NodeLogFactory = ProjectFactory()
        self.pointer = ProjectFactory()

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_url = '/{}nodes/{}/logs/'.format(API_BASE, self.private_project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/logs/'.format(API_BASE, self.public_project._id)

    def tearDown(self):
        super(TestNodeLogList, self).tearDown()
        NodeLog.remove()

    def test_add_tag(self):
        user_auth = Auth(self.user)
        self.public_project.add_tag("Jeff Spies", auth=user_auth)
        assert_equal("tag_added", self.public_project.logs[OSF_LATEST].action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'tag_added')
        assert_equal("Jeff Spies", self.public_project.logs[OSF_LATEST].params['tag'])

    def test_remove_tag(self):
        user_auth = Auth(self.user)
        self.public_project.add_tag("Jeff Spies", auth=user_auth)
        assert_equal("tag_added", self.public_project.logs[OSF_LATEST].action)
        self.public_project.remove_tag("Jeff Spies", auth=self.user_auth)
        assert_equal("tag_removed", self.public_project.logs[OSF_LATEST].action)
        res = self.app.get(self.public_url, auth=self.user)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'tag_removed')
        assert_equal("Jeff Spies", self.public_project.logs[OSF_LATEST].params['tag'])

    def test_project_created(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_equal(self.public_project.logs[OSF_FIRST].action, "project_created")
        assert_equal(self.public_project.logs[OSF_FIRST].action,res.json['data'][API_LATEST]['attributes']['action'])

    def test_log_create_on_public_project(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_datetime_equal(parse_date(res.json['data'][API_FIRST]['attributes']['date']),
                              self.public_project.logs[OSF_FIRST].date)
        assert_equal(res.json['data'][API_FIRST]['attributes']['action'], self.public_project.logs[OSF_FIRST].action)

    def test_log_create_on_private_project(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_datetime_equal(datetime.datetime.strptime(res.json['data'][API_FIRST]['attributes']['date'], "%Y-%m-%dT%H:%M:%S.%f"),
                              self.private_project.logs[OSF_FIRST].date)
        assert_equal(res.json['data'][API_FIRST]['attributes']['action'], self.private_project.logs[OSF_FIRST].action)

    def test_add_addon(self):
        self.public_project.add_addon('github', auth=self.user_auth)
        assert_equal('addon_added', self.public_project.logs[OSF_LATEST].action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'addon_added')

    def test_project_add_remove_contributor(self):
        self.public_project.add_contributor(self.contrib, auth=self.user_auth)
        assert_equal('contributor_added', self.public_project.logs[OSF_LATEST].action)
        self.public_project.remove_contributor(self.contrib, auth=self.user_auth)
        assert_equal('contributor_removed', self.public_project.logs[OSF_LATEST].action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'contributor_removed')
        assert_equal(res.json['data'][1]['attributes']['action'], 'contributor_added')

    def test_remove_addon(self):
        self.public_project.add_addon('github', auth=self.user_auth)
        assert_equal('addon_added', self.public_project.logs[OSF_LATEST].action)
        self.public_project.delete_addon('github', auth=self.user_auth)
        assert_equal('addon_removed', self.public_project.logs[OSF_LATEST].action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'addon_removed')

    def test_add_pointer(self):
        self.public_project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        assert_equal('pointer_created', self.public_project.logs[OSF_LATEST].action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), len(self.public_project.logs))
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'pointer_created')


class TestNodeLogFiltering(TestNodeLogList):

    def test_filter_action_not_equal(self):
        self.public_project.add_tag("Jeff Spies", auth=self.user_auth)
        assert_equal("tag_added", self.public_project.logs[OSF_LATEST].action)
        url = '/{}nodes/{}/logs/?filter[action][ne]=tag_added'.format(API_BASE, self.public_project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['action'], 'project_created')

    def test_filter_date_not_equal(self):
        self.public_project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        assert_equal('pointer_created', self.public_project.logs[OSF_LATEST].action)
        assert_equal(len(self.public_project.logs), 2)
        date_pointer_added = str(self.public_project.logs[1].date).replace(' ', 'T')

        url = '/{}nodes/{}/logs/?filter[date][ne]={}'.format(API_BASE, self.public_project._id, date_pointer_added)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['action'], 'project_created')
