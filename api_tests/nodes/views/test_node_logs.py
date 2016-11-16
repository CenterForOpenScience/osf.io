import urlparse

import pytz
from nose.tools import *  # flake8: noqa
from dateutil.parser import parse as parse_date
import pytest

from framework.auth.core import Auth
from website.models import NodeLog
from website.util import disconnected_from_listeners
from website.project.signals import contributor_removed
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, assert_datetime_equal
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)
import datetime


API_LATEST = 0
API_FIRST = -1


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
        self.private_url = '/{}nodes/{}/logs/?version=2.2'.format(API_BASE, self.private_project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/logs/?version=2.2'.format(API_BASE, self.public_project._id)

    def test_add_tag(self):
        user_auth = Auth(self.user)
        self.public_project.add_tag("Jeff Spies", auth=user_auth)
        assert_equal("tag_added", self.public_project.logs.latest().action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'tag_added')
        assert_equal("Jeff Spies", self.public_project.logs.latest().params['tag'])

    def test_remove_tag(self):
        user_auth = Auth(self.user)
        self.public_project.add_tag("Jeff Spies", auth=user_auth)
        assert_equal("tag_added", self.public_project.logs.latest().action)
        self.public_project.remove_tag("Jeff Spies", auth=self.user_auth)
        assert_equal("tag_removed", self.public_project.logs.latest().action)
        res = self.app.get(self.public_url, auth=self.user)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'tag_removed')
        assert_equal("Jeff Spies", self.public_project.logs.latest().params['tag'])

    def test_project_created(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_equal(self.public_project.logs.first().action, 'project_created')
        assert_equal(self.public_project.logs.first().action, res.json['data'][API_LATEST]['attributes']['action'])

    def test_log_create_on_public_project(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_datetime_equal(parse_date(res.json['data'][API_FIRST]['attributes']['date']),
                              self.public_project.logs.first().date)
        assert_equal(res.json['data'][API_FIRST]['attributes']['action'], self.public_project.logs.first().action)

    def test_log_create_on_private_project(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_datetime_equal(parse_date(res.json['data'][API_FIRST]['attributes']['date']),
                              self.private_project.logs.first().date)
        assert_equal(res.json['data'][API_FIRST]['attributes']['action'], self.private_project.logs.first().action)

    def test_add_addon(self):
        self.public_project.add_addon('github', auth=self.user_auth)
        assert_equal('addon_added', self.public_project.logs.latest().action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'addon_added')

    def test_project_add_remove_contributor(self):
        self.public_project.add_contributor(self.contrib, auth=self.user_auth)
        assert_equal('contributor_added', self.public_project.logs.latest().action)
        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            self.public_project.remove_contributor(self.contrib, auth=self.user_auth)
        assert_equal('contributor_removed', self.public_project.logs.latest().action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'contributor_removed')
        assert_equal(res.json['data'][1]['attributes']['action'], 'contributor_added')

    def test_remove_addon(self):
        self.public_project.add_addon('github', auth=self.user_auth)
        assert_equal('addon_added', self.public_project.logs.latest().action)
        old_log_length = len(list(self.public_project.logs.all()))
        self.public_project.delete_addon('github', auth=self.user_auth)
        assert_equal('addon_removed', self.public_project.logs.latest().action)
        assert_equal((self.public_project.logs.count() - 1), old_log_length)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'addon_removed')

    def test_add_pointer(self):
        self.public_project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        assert_equal('pointer_created', self.public_project.logs.latest().action)
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), self.public_project.logs.count())
        assert_equal(res.json['data'][API_LATEST]['attributes']['action'], 'pointer_created')


class TestNodeLogFiltering(TestNodeLogList):

    def test_filter_action_not_equal(self):
        self.public_project.add_tag("Jeff Spies", auth=self.user_auth)
        assert_equal("tag_added", self.public_project.logs.latest().action)
        url = '/{}nodes/{}/logs/?filter[action][ne]=tag_added'.format(API_BASE, self.public_project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['action'], 'project_created')

    def test_filter_date_not_equal(self):
        self.public_project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        assert_equal('pointer_created', self.public_project.logs.latest().action)
        assert_equal(self.public_project.logs.count(), 2)

        pointer_added_log = self.public_project.logs.get(action='pointer_created')
        date_pointer_added = str(pointer_added_log.date).split('+')[0].replace(' ', 'T')

        url = '/{}nodes/{}/logs/?filter[date][ne]={}'.format(API_BASE, self.public_project._id, date_pointer_added)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['action'], 'project_created')
