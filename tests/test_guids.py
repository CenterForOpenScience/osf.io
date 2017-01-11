# -*- coding: utf-8 -*-

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import NodeFactory

from modularodm import Q
from modularodm import fields

from framework.mongo.storage import MongoStorage
from framework.mongo import database
from framework.guid.model import GuidStoredObject

from website import models


class TestGuidStoredObject(OsfTestCase):

    def test_guid_stored_object(self):
        class FakeSchema(GuidStoredObject):
            _id = fields.StringField()
            @property
            def deep_url(self):
                return 'http://dinosaurs.sexy'
        FakeSchema.set_storage(MongoStorage(database, 'fakeschema'))
        fake_guid = FakeSchema(_id='fake')
        fake_guid.save()
        guids = models.Guid.find(Q('_id', 'eq', 'fake'))
        assert_equal(guids.count(), 1)
        assert_equal(guids[0].referent, fake_guid)
        assert_equal(guids[0]._id, fake_guid._id)


class TestResolveGuid(OsfTestCase):

    def setUp(self):
        super(TestResolveGuid, self).setUp()
        self.node = NodeFactory()

    def test_resolve_guid(self):
        res_guid = self.app.get(self.node.web_url_for('node_setting', _guid=True), auth=self.node.creator.auth)
        res_full = self.app.get(self.node.web_url_for('node_setting'), auth=self.node.creator.auth)
        assert_equal(res_guid.text, res_full.text)

    def test_resolve_guid_no_referent(self):
        guid = models.Guid.load(self.node._id)
        guid.referent = None
        guid.save()
        res = self.app.get(
            self.node.web_url_for('node_setting', _guid=True),
            auth=self.node.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)

    @mock.patch('website.project.model.Node.deep_url', None)
    def test_resolve_guid_no_url(self):
        res = self.app.get(
            self.node.web_url_for('node_setting', _guid=True),
            auth=self.node.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
