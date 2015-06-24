
import mock
from collections import OrderedDict

from website.notifications.events.model import *

from framework.auth import Auth
from tests import factories
from tests.base import OsfTestCase


class TestEventGet(OsfTestCase):
    """
    Add all possible called events here to ensure that the Event class can call them.
    """
    def setUp(self):
        super(TestEventGet, self).setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.node = factories.ProjectFactory(creator=self.user)

    def test_get_file_updated(self):
        """Event gets FileUpdated from file_updated"""
        event = Event.get_event(self.user, self.node, 'file_updated', payload=file_payload)
        self.assertIsInstance(event, FileUpdated)

    def test_get_file_added(self):
        """Event gets FileAdded from file_added"""
        event = Event.get_event(self.user, self.node, 'file_added', payload=file_payload)
        self.assertIsInstance(event, FileAdded)

    def test_get_file_removed(self):
        """Event gets FileRemoved from file_removed"""
        event = Event.get_event(self.user, self.node, 'file_removed', payload=file_deleted_payload)
        self.assertIsInstance(event, FileRemoved)

    def test_get_folder_created(self):
        """Event gets FolderCreated from folder_created"""
        event = Event.get_event(self.user, self.node, 'folder_created', payload=folder_created_payload)
        self.assertIsInstance(event, FolderCreated)

    def test_get_file_moved(self):
        """Event gets AddonFileMoved from addon_file_moved"""
        file_moved_payload = file_move_payload(self.node, self.node)
        event = Event.get_event(self.user, self.node, 'addon_file_moved', payload=file_moved_payload)
        self.assertIsInstance(event, AddonFileMoved)

    def test_get_file_copied(self):
        """Event gets AddonFileCopied from addon_file_copied"""

        file_copied_payload = file_copy_payload(self.node, self.node)
        event = Event.get_event(self.user, self.node, 'addon_file_copied', payload=file_copied_payload)
        self.assertIsInstance(event, AddonFileCopied)

    def tearDown(self):
        pass


class TestFileEventModel(OsfTestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

file_payload = OrderedDict([(u'action', u'update'),
                            (u'auth', OrderedDict([(u'email', u'tgn6m@osf.io'), (u'id', u'tgn6m'), (u'name', u'aab')])),
                            (u'metadata', OrderedDict([(u'contentType', None),
                                                       (u'etag', u'10485efa4069bb94d50588df2e7466a079d49d4f5fd7bf5b35e7c0d5b12d76b7'),
                                                       (u'extra', OrderedDict([(u'downloads', 0),
                                                                               (u'version', 30)])),
                                                       (u'kind', u'file'),
                                                       (u'materialized', u'/One/Paper13.txt'),
                                                       (u'modified', u'Wed, 24 Jun 2015 10:45:01 '),
                                                       (u'name', u'Paper13.txt'),
                                                       (u'path', u'5581cb50a24f710b0f4623f9'),
                                                       (u'provider', u'osfstorage'),
                                                       (u'size', 2008)])),
                            (u'provider', u'osfstorage'),
                            (u'time', 1435157161.979904)])

file_deleted_payload = OrderedDict([
    (u'action', u'delete'),
    (u'auth', OrderedDict([
        (u'email', u'tgn6m@osf.io'),
        (u'id', u'tgn6m'),
        (u'name', u'aab')])),
    (u'metadata', OrderedDict([
        (u'materialized', u'/Two/Paper13.txt'),
        (u'path', u'Two/Paper13.txt')])),
    (u'provider', u'osfstorage'),
    (u'time', 1435157876.690203)])

folder_created_payload = OrderedDict([
    (u'action', u'create_folder'),
    (u'auth', OrderedDict([
        (u'email', u'tgn6m@osf.io'),
        (u'id', u'tgn6m'),
        (u'name', u'aab')])),
    (u'metadata', OrderedDict([
        (u'etag', u'5caf8ab73c068565297e455ebce37fd64b6897a2284ec9d7ecba8b6093082bcd'),
        (u'extra', OrderedDict()),
        (u'kind', u'folder'),
        (u'materialized', u'/Three/'),
        (u'name', u'Three'),
        (u'path', u'558ac595a24f714eff336d66/'),
        (u'provider', u'osfstorage')])),
    (u'provider', u'osfstorage'),
    (u'time', 1435157969.475282)])


def file_move_payload(new_node, old_node):
    return OrderedDict([
        (u'action', u'move'),
        (u'auth', OrderedDict([
            (u'email', 'Bob'),
            (u'id', 'bob2'),
            (u'name', 'Bob')])),
        (u'destination', OrderedDict([
            (u'contentType', None),
            (u'etag', u'10485efa4069bb94d50588df2e7466a079d49d4f5fd7bf5b35e7c0d5b12d76b7'),
            (u'extra', OrderedDict([
                (u'downloads', 0),
                (u'version', 30)])),
            (u'kind', u'file'),
            (u'materialized', u'Three/Paper13.txt'),
            (u'modified', None),
            (u'name', u'Paper13.txt'),
            (u'nid', str(old_node)),
            (u'path', u'/5581cb50a24f710b0f4623f9'),
            (u'provider', u'osfstorage'),
            (u'size', 2008),
            ('url', '/project/nhgts/files/osfstorage/5581cb50a24f710b0f4623f9/'),
            ('node', {'url': '/nhgts/', '_id': old_node._id, 'title': u'Consolidate'}),
            ('addon', 'OSF Storage')])),
        (u'source', OrderedDict([
            (u'materialized', u'One/Paper13.txt'),
            (u'name', u'Paper13.txt'),
            (u'nid', str(new_node)),
            (u'path', u'One/Paper13.txt'),
            (u'provider', u'osfstorage'),
            ('url', '/project/nhgts/files/osfstorage/One/Paper13.txt/'),
            ('node', {'url': '/nhgts/', '_id': new_node._id, 'title': u'Consolidate'}),
            ('addon', 'OSF Storage')])),
        (u'time', 1435158051.204264),
        ('node', u'nhgts'),
        ('project', None)])


def file_copy_payload(new_node, old_node):
    return OrderedDict([
        (u'action', u'copy'),
        (u'auth', OrderedDict([
            (u'email', u'tgn6m@osf.io'),
            (u'id', u'tgn6m'),
            (u'name', u'aab')])),
        (u'destination', OrderedDict([
            (u'contentType', None),
            (u'etag', u'16075ae3e546971003095beef8323584de40b1fcbf52ed4bb9e7f8547e322824'),
            (u'extra', OrderedDict([
                (u'downloads', 0),
                (u'version', 30)])),
            (u'kind', u'file'),
            (u'materialized', u'Two/Paper13.txt'),
            (u'modified', None),
            (u'name', u'Paper13.txt'),
            (u'nid', u'nhgts'),
            (u'path', u'/558ac45da24f714eff336d59'),
            (u'provider', u'osfstorage'),
            (u'size', 2008),
            ('url', '/project/nhgts/files/osfstorage/558ac45da24f714eff336d59/'),
            ('node', {'url': '/nhgts/', '_id': old_node._id, 'title': u'Consolidate'}),
            ('addon', 'OSF Storage')])),
        (u'source', OrderedDict([
            (u'materialized', u'One/Paper13.txt'),
            (u'name', u'Paper13.txt'),
            (u'nid', u'nhgts'),
            (u'path', u'One/Paper13.txt'),
            (u'provider', u'osfstorage'),
            ('url', '/project/nhgts/files/osfstorage/One/Paper13.txt/'),
            ('node', {'url': '/nhgts/', '_id': new_node._id, 'title': u'Consolidate'}),
            ('addon', 'OSF Storage')])),
        (u'time', 1435157658.036183),
        ('node', u'nhgts'),
        ('project', None)])

