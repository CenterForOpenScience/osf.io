# -*- coding: utf-8 -*-
"""Notifications tests"""
import unittest
from nose.tools import *
import mock

from framework.auth import Auth
from website import settings
from tests.base import OsfTestCase
from tests import factories

from furl import furl
from website.addons.base import notifications


class TestNotifications(OsfTestCase):
    def setUp(self):
        super(TestNotifications, self).setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.node = factories.ProjectFactory(creator=self.user)
        self.move_copy_payload = dict(
            destination=dict(
                node={"title": self.node.title},
                path='string',
                provider='osfstorage',
                materialized='other/that.txt',
                addon='OSF Storage'
            ),
            source=dict(
                node={"_id": self.node._id, "title": self.node.title},
                provider='osfstorage',
                materialized='this/that.txt',
                addon='OSF Storage'
            )
        )
        self.other_payload = dict(
            provider='osfstorage',
            metadata=dict(
                path='string',
                materialized='this/that.txt'
            )
        )
        self.f_url = furl(self.node.absolute_url)

    @mock.patch('website.notifications.emails.notify')
    @mock.patch('website.addons.base.notifications.file_created',
                return_value=('event_sub', furl('localhost:5000/crazy'), 'message'))
    def test_file_notify(self, file_added, notify):
        event = 'file_added'
        payload = self.other_payload
        notifications.file_notify(self.user, self.node, event, payload)
        assert_true(file_added.called)
        # assert_true(notify.called)

    def test_file_info(self):
        notifications.file_info(self.node, self.other_payload['metadata']['path'], self.other_payload['provider'])

    @mock.patch('website.addons.base.notifications.file_info',
                return_value=('crazy', 'crazy_file_updated', '/crazy/'))
    def test_file_created(self, file_info):
        event_sub, f_url, message = notifications.file_created(self.node, self.f_url, self.other_payload)
        assert_equal(event_sub, 'crazy_file_updated')
        assert_equal(settings.DOMAIN + 'crazy/', f_url.url)
        assert_equal(message, 'added file "<b>this/that.txt</b>".')

    @mock.patch('website.addons.base.notifications.file_info',
                return_value=('crazy', 'crazy_file_updated', '/crazy/'))
    def test_file_updated(self, file_info):
        event_sub, f_url, message = notifications.file_updated(self.node, self.f_url, self.other_payload)
        assert_equal(event_sub, 'crazy_file_updated')
        assert_equal(message, 'updated file "<b>this/that.txt</b>".')
        assert_equal(settings.DOMAIN + 'crazy/', f_url.url)

    def test_file_deleted(self):
        event_sub, f_url, message = notifications.file_deleted(self.node, self.f_url, self.other_payload)
        assert_equal(event_sub, 'file_updated')
        assert_equal(message, 'removed file "<b>this/that.txt</b>".')
        assert_equal(settings.DOMAIN + 'project/' + self.node._id + '/files/', f_url.url)

    def test_folder_added(self):
        event_sub, f_url, message = notifications.folder_added(self.node, self.f_url, self.other_payload)
        assert_equal(event_sub, 'file_updated')
        assert_equal(message, 'created folder "<b>this/that.txt</b>".')
        assert_equal(settings.DOMAIN + 'project/' +self.node._id + '/files/', f_url.url)

    @mock.patch('website.notifications.utils.move_file_subscription')
    @mock.patch('website.notifications.emails.remove_users_from_subscription')
    @mock.patch('website.addons.base.notifications.file_info',
                return_value=('crazy', 'crazy_file_updated', '/crazy/'))
    def test_file_moved(self, file_info, remove, move):
        event_sub, f_url, message = notifications.file_moved(self.node, self.f_url, self.move_copy_payload, self.user)
        assert_equal(event_sub, 'crazy_file_updated')
        assert_equal(settings.DOMAIN + 'crazy/', f_url.url)
        assert_equal(message, 'moved "<b>this/that.txt</b>" from OSF Storage in The meaning of life to "<b>other/that.txt</b>" in OSF Storage in The meaning of life.')

    @mock.patch('website.addons.base.notifications.file_info',
                return_value=('crazy', 'crazy_file_updated', '/crazy/'))
    def test_file_copied(self, file_info):
        event_sub, f_url, message = notifications.file_copied(self.node, self.f_url, self.move_copy_payload)
        assert_equal(message, 'copied "<b>this/that.txt</b>" from OSF Storage in The meaning of life to "<b>other/that.txt</b>" in OSF Storage in The meaning of life.')
        assert_equal(event_sub, 'crazy_file_updated')
        assert_equal(settings.DOMAIN + 'crazy/', f_url.url)
