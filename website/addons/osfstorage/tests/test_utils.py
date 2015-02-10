#!/usr/bin/env python
# encoding: utf-8

from nose.tools import *  # noqa

from tests.factories import AuthUserFactory

import furl

from framework import sessions
from framework.flask import request

from website.models import Session
from website.addons.osfstorage.tests import factories
from website.addons.osfstorage import model
from website.addons.osfstorage import views
from website.addons.osfstorage import utils

from website.addons.osfstorage.tests.utils import (
    StorageTestCase, Delta, AssertDeltas
)


class TestHGridUtils(StorageTestCase):

    def test_serialize_metadata_folder(self):
        file_tree = model.OsfStorageFileTree(
            path='god/save/the/queen',
            node_settings=self.project.get_addon('osfstorage'),
        )
        serialized = utils.serialize_metadata_hgrid(
            file_tree,
            self.project,
        )
        assert_equal(serialized['path'], 'god/save/the/queen')
        assert_equal(serialized['name'], 'queen')
        assert_equal(serialized['ext'], '')
        assert_equal(serialized['kind'], 'folder')

    def test_serialize_metadata_file(self):
        file_record = model.OsfStorageFileRecord(
            path='kind/of/<strong>magic.mp3',
            node_settings=self.project.get_addon('osfstorage'),
        )
        serialized = utils.serialize_metadata_hgrid(
            file_record,
            self.project,
        )
        assert_equal(
            serialized['path'],
            'kind/of/<strong>magic.mp3',
        )
        assert_equal(
            serialized['name'],
            '<strong>magic.mp3',
        )
        assert_equal(serialized['ext'], '.mp3')
        assert_equal(serialized['kind'], 'file')

    def test_get_item_kind_folder(self):
        assert_equal(
            utils.get_item_kind(model.OsfStorageFileTree()),
            'folder',
        )

    def test_get_item_kind_file(self):
        assert_equal(
            utils.get_item_kind(model.OsfStorageFileRecord()),
            'file',
        )

    def test_get_item_kind_invalid(self):
        with assert_raises(TypeError):
            utils.get_item_kind('pizza')


class TestGetCookie(StorageTestCase):

    def test_get_cookie(self):
        user = AuthUserFactory()
        create_delta = Delta(lambda: Session.find().count(), lambda value: value + 1)
        with AssertDeltas(create_delta):
            utils.get_cookie_for_user(user)
        get_delta = Delta(lambda: Session.find().count())
        with AssertDeltas(get_delta):
            utils.get_cookie_for_user(user)


class TestGetDownloadUrl(StorageTestCase):

    def setUp(self):
        super(TestGetDownloadUrl, self).setUp()
        self.path = 'frozen/pizza/reviews.gif'
        self.record, _ = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        for _ in range(3):
            version = factories.FileVersionFactory()
            self.record.versions.append(version)
        self.record.save()

    def test_get_filename_latest_version(self):
        filename = utils.get_filename(3, self.record.versions[-1], self.record)
        assert_equal(filename, self.record.name)

    def test_get_filename_not_latest_version(self):
        filename = utils.get_filename(2, self.record.versions[-2], self.record)
        expected = ''.join([
            'reviews-',
            self.record.versions[-2].date_created.isoformat(),
            '.gif',
        ])
        assert_equal(filename, expected)

    def test_get_waterbutler_url(self):
        user = AuthUserFactory()
        path = ('test', 'endpoint')
        query = {'some': 'field'}
        test_url = utils.get_waterbutler_url(user, *path, **query)
        url = furl.furl(test_url)

        assert_equal(url.path.segments[0], 'test')
        assert_equal(url.path.segments[1], 'endpoint')
        assert_equal(url.args['some'], 'field')
        assert_not_in('view_only', url.args)

    def test_get_waterbutler_url_view_only(self):
        user = AuthUserFactory()
        path = ('test', 'endpoint')
        query = {'view_only': 'secret_key'}
        test_url = utils.get_waterbutler_url(user, *path, **query)
        url = furl.furl(test_url)

        assert_equal(url.args['view_only'], 'secret_key')


class TestSerializeRevision(StorageTestCase):

    def setUp(self):
        super(TestSerializeRevision, self).setUp()
        self.path = 'kind/of/magic.mp3'
        self.record, _ = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        self.versions = [
            factories.FileVersionFactory(creator=self.user)
            for _ in range(3)
        ]
        self.record.versions = self.versions
        self.record.save()

    def test_serialize_revision(self):
        sessions.sessions[request._get_current_object()] = Session()
        views.update_analytics(self.project, self.path, 1)
        views.update_analytics(self.project, self.path, 1)
        views.update_analytics(self.project, self.path, 3)
        expected = {
            'index': 1,
            'user': {
                'name': self.user.fullname,
                'url': self.user.url,
            },
            'date': self.versions[0].date_created.isoformat(),
            'downloads': 2,
        }
        observed = utils.serialize_revision(
            self.project,
            self.record,
            self.versions[0],
            1,
        )
        assert_equal(expected, observed)
