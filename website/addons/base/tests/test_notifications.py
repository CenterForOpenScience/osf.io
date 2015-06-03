# -*- coding: utf-8 -*-
"""Notifications tests"""
import unittest
from nose.tools import *
import mock

from framework.auth import Auth
from website.util import api_url_for, web_url_for
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

    # Should test all the event options.
    @mock.patch('website.notifications.emails.notify')
    def test_file_notify(self, notify):
        event = 'file_added'
        payload = self.other_payload
        notifications.file_notify(self.user, self.node, event, payload)
        assert_true(notify.called)

    def test_file_info(self):
        notifications.file_info(self.node, self.other_payload['metadata']['path'], self.other_payload['provider'])

    def test_file_created(self):
        notifications.file_created(self.node, self.f_url, self.other_payload)

    def test_file_updated(self):
        notifications.file_updated(self.node, self.f_url, self.other_payload)

    def test_file_deleted(self):
        notifications.file_deleted(self.node, self.f_url, self.other_payload)

    def test_folder_added(self):
        notifications.folder_added(self.node, self.f_url, self.other_payload)

    # mock call to updating subscription
    def test_file_moved(self):
        notifications.file_moved(self.node, self.f_url, self.move_copy_payload, self.user)

    def test_file_copied(self):
        notifications.file_copied(self.node, self.f_url, self.move_copy_payload)