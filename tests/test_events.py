
import mock
from nose.tools import *
from collections import OrderedDict

from website.notifications.events.model import *
from website.notifications.events.utils import *

from framework.auth import Auth
from tests import factories
from tests.base import OsfTestCase


class TestListOfFiles(OsfTestCase):
    """
    List files given a list
    """
    def setUp(self):
        super(TestListOfFiles, self).setUp()
        self.tree = {
            'kind': 'folder',
            'path': 'a',
            'children': [
                {
                    'kind': 'folder',
                    'path': 'b',
                    'children': [
                        {
                            'kind': 'file',
                            'path': 'e'
                        },
                        {
                            'kind': 'file',
                            'path': 'f'
                        }
                    ]
                },
                {
                    'kind': 'file',
                    'path': 'c'
                },
                {
                    'kind': 'file',
                    'path': 'd'
                }
            ]
        }

    def test_list_of_files(self):
        files = []
        list_of_files(self.tree, files)
        assert_equal(['e', 'f', 'c', 'd'], files)

    def tearDown(self):
        pass


class TestParseEvent(OsfTestCase):
    """
    Add all possible called events here to ensure that the Event class can call them.
    """
    def setUp(self):
        super(TestParseEvent, self).setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.node = factories.ProjectFactory(creator=self.user)

    def test_get_file_updated(self):
        """Event gets FileUpdated from file_updated"""
        event = Event.parse_event(self.user, self.node, 'file_updated', payload=file_payload)
        self.assertIsInstance(event, FileUpdated)

    def test_get_file_added(self):
        """Event gets FileAdded from file_added"""
        event = Event.parse_event(self.user, self.node, 'file_added', payload=file_payload)
        self.assertIsInstance(event, FileAdded)

    def test_get_file_removed(self):
        """Event gets FileRemoved from file_removed"""
        event = Event.parse_event(self.user, self.node, 'file_removed', payload=file_deleted_payload)
        self.assertIsInstance(event, FileRemoved)

    def test_get_folder_created(self):
        """Event gets FolderCreated from folder_created"""
        event = Event.parse_event(self.user, self.node, 'folder_created', payload=folder_created_payload)
        self.assertIsInstance(event, FolderCreated)

    def test_get_file_moved(self):
        """Event gets AddonFileMoved from addon_file_moved"""
        file_moved_payload = file_move_payload(self.node, self.node)
        event = Event.parse_event(self.user, self.node, 'addon_file_moved', payload=file_moved_payload)
        self.assertIsInstance(event, AddonFileMoved)

    def test_get_file_copied(self):
        """Event gets AddonFileCopied from addon_file_copied"""
        file_copied_payload = file_copy_payload(self.node, self.node)
        event = Event.parse_event(self.user, self.node, 'addon_file_copied', payload=file_copied_payload)
        self.assertIsInstance(event, AddonFileCopied)

    def tearDown(self):
        pass


class TestFileUpdated(OsfTestCase):
    def setUp(self):
        super(TestFileUpdated, self).setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_file_updated',
            owner=self.project,
            event_name='file_updated'
        )
        self.project_subscription.save()
        self.user2 = factories.UserFactory()
        self.event = Event.parse_event(self.user2, self.project, 'file_updated', payload=file_payload)

    def test_info_formed_correct(self):
        assert_equal('{}_file_updated'.format(wb_path), self.event.event)
        assert_equal('updated file "<b>{}</b>".'.format(materialized.lstrip('/')), self.event.html_message)
        assert_equal('updated file "{}".'.format(materialized.lstrip('/')), self.event.text_message)

    @mock.patch('website.notifications.emails.notify')
    def test_file_updated(self, mock_notify):
        self.event.perform()
        # notify('exd', 'file_updated', 'user', self.project, datetime.utcnow())
        assert_true(mock_notify.called)

    def tearDown(self):
        pass


class TestFileAdded(OsfTestCase):
    def setUp(self):
        super(TestFileAdded, self).setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_file_updated',
            owner=self.project,
            event_name='file_updated'
        )
        self.project_subscription.save()
        self.user2 = factories.UserFactory()
        self.event = Event.parse_event(self.user2, self.project, 'file_added', payload=file_payload)

    def test_info_formed_correct(self):
        assert_equal('{}_file_updated'.format(wb_path), self.event.event)
        assert_equal('added file "<b>{}</b>".'.format(materialized.lstrip('/')), self.event.html_message)
        assert_equal('added file "{}".'.format(materialized.lstrip('/')), self.event.text_message)

    @mock.patch('website.notifications.emails.notify')
    def test_file_added(self, mock_notify):
        self.event.perform()
        # notify('exd', 'file_updated', 'user', self.project, datetime.utcnow())
        assert_true(mock_notify.called)

    def tearDown(self):
        pass


class TestFileRemoved(OsfTestCase):
    def setUp(self):
        super(TestFileRemoved, self).setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_file_updated',
            owner=self.project,
            event_name='file_updated'
        )
        self.project_subscription.save()
        self.user2 = factories.UserFactory()
        self.event = Event.parse_event(self.user2, self.project, 'file_removed', payload=file_deleted_payload)

    def test_info_formed_correct(self):
        assert_equal('file_updated', self.event.event)
        assert_equal('removed file "<b>{}</b>".'.format(materialized.lstrip('/')), self.event.html_message)
        assert_equal('removed file "{}".'.format(materialized.lstrip('/')), self.event.text_message)

    @mock.patch('website.notifications.emails.notify')
    def test_file_removed(self, mock_notify):
        self.event.perform()
        # notify('exd', 'file_updated', 'user', self.project, datetime.utcnow())
        assert_true(mock_notify.called)

    def tearDown(self):
        pass


class TestFolderCreated(OsfTestCase):
    def setUp(self):
        super(TestFolderCreated, self).setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_file_updated',
            owner=self.project,
            event_name='file_updated'
        )
        self.project_subscription.save()
        self.user2 = factories.UserFactory()
        self.event = Event.parse_event(self.user2, self.project, 'folder_created', payload=folder_created_payload)

    def test_info_formed_correct(self):
        assert_equal('file_updated', self.event.event)
        assert_equal('created folder "<b>Three/</b>".', self.event.html_message)
        assert_equal('created folder "Three/".', self.event.text_message)

    @mock.patch('website.notifications.emails.notify')
    def test_folder_added(self, mock_notify):
        self.event.perform()
        # notify('exd', 'file_updated', 'user', self.project, datetime.utcnow())
        assert_true(mock_notify.called)

    def tearDown(self):
        pass


class TestFileMoved(OsfTestCase):
    def setUp(self):
        super(TestFileMoved, self).setUp()
        self.user_1 = factories.AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.user_2 = factories.AuthUserFactory()
        self.user_3 = factories.AuthUserFactory()
        self.user_4 = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user_1)
        self.private_node = factories.NodeFactory(parent=self.project, is_public=False, creator=self.user_1)
        # Payload
        file_moved_payload = file_move_payload(self.private_node, self.project)
        self.event = Event.parse_event(self.user_2, self.private_node, 'addon_file_moved', payload=file_moved_payload)
        # Subscriptions
        # for parent node
        self.sub = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_file_updated',
            owner=self.project,
            event_name='file_updated'
        )
        self.sub.save()
        # for private node
        self.private_sub = factories.NotificationSubscriptionFactory(
            _id=self.private_node._id + '_file_updated',
            owner=self.private_node,
            event_name='file_updated'
        )
        self.private_sub.save()
        # for file subscription
        self.file_sub = factories.NotificationSubscriptionFactory(
            _id='{pid}_{wbid}_file_updated'.format(
                pid=self.project._id,
                wbid=self.event.waterbutler_id
            ),
            owner=self.project,
            event_name='xyz42_file_updated'
        )
        self.file_sub.save()

    def test_info_formed_correct(self):
        """Move Event: Ensures data is correctly formatted"""
        assert_equal('{}_file_updated'.format(wb_path), self.event.event)
        # assert_equal('moved file "<b>{}</b>".', self.event.html_message)
        # assert_equal('created folder "Three/".', self.event.text_message)

    @mock.patch('website.notifications.emails.store_emails')
    def test_user_performing_action_no_email(self, mock_store):
        """Move Event: Makes sure user who performed the action is not included in the notifications"""
        self.sub.email_digest.append(self.user_2)
        self.sub.save()
        self.event.perform()
        assert_equal(0, mock_store.call_count)

    @mock.patch('website.notifications.emails.store_emails')
    def test_perform_store_called_once(self, mock_store):
        """Move Event: Tests that store_emails is called once from perform"""
        self.sub.email_transactional.append(self.user_1)
        self.sub.save()
        self.event.perform()
        assert_equal(1, mock_store.call_count)

    @mock.patch('website.notifications.emails.store_emails')
    def test_perform_store_one_of_each(self, mock_store):
        """Move Event: Tests that store_emails is called 3 times, one in each category"""
        self.sub.email_transactional.append(self.user_1)
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        self.sub.email_digest.append(self.user_3)
        self.sub.save()
        self.project.add_contributor(self.user_4, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.file_sub.email_digest.append(self.user_4)
        self.file_sub.save()
        self.event.perform()
        assert_equal(3, mock_store.call_count)

    @mock.patch('website.notifications.emails.store_emails')
    def test_remove_user_sent_once(self, mock_store):
        """Move Event: Tests removed user is removed once. Regression"""
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.file_sub.email_digest.append(self.user_3)
        self.file_sub.save()
        self.event.perform()
        assert_equal(1, mock_store.call_count)

    def tearDown(self):
        pass


class TestCategorizeUsers(OsfTestCase):
    def setUp(self):
        super(TestCategorizeUsers, self).setUp()
        self.user_1 = factories.AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.user_2 = factories.AuthUserFactory()
        self.user_3 = factories.AuthUserFactory()
        self.user_4 = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user_1)
        self.private_node = factories.NodeFactory(parent=self.project, is_public=False, creator=self.user_1)
        # Payload
        file_moved_payload = file_move_payload(self.private_node, self.project)
        self.event = Event.parse_event(self.user_2, self.private_node, 'addon_file_moved',
                                       payload=file_moved_payload)
        # Subscriptions
        # for parent node
        self.sub = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_file_updated',
            owner=self.project,
            event_name='file_updated'
        )
        self.sub.save()
        # for private node
        self.private_sub = factories.NotificationSubscriptionFactory(
            _id=self.private_node._id + '_file_updated',
            owner=self.private_node,
            event_name='file_updated'
        )
        self.private_sub.save()
        # for file subscription
        self.file_sub = factories.NotificationSubscriptionFactory(
            _id='{pid}_{wbid}_file_updated'.format(
                pid=self.project._id,
                wbid=self.event.waterbutler_id
            ),
            owner=self.project,
            event_name='xyz42_file_updated'
        )
        self.file_sub.save()

    def test_warn_user(self):
        """Tests that a user with a sub in the origin node gets a warning that they are no longer tracking the file."""
        self.sub.email_transactional.append(self.user_1)
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        self.sub.email_digest.append(self.user_3)
        self.sub.save()
        self.private_sub.none.append(self.user_3)
        self.private_sub.save()
        moved, warn, removed = categorize_users(self.event.user, self.event.event, self.event.source_node,
                                                self.event.event, self.event.node)
        assert_equal({'email_transactional': [], 'email_digest': [self.user_3._id], 'none': []}, warn)
        assert_equal({'email_transactional': [self.user_1._id], 'email_digest': [], 'none': []}, moved)
        # print (warn, moved, removed)

    def test_moved_user(self):
        """Doesn't warn a user with two different subs, but does send a moved email"""
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        self.sub.email_digest.append(self.user_3)
        self.sub.save()
        self.private_sub.email_transactional.append(self.user_3)
        self.private_sub.save()
        moved, warn, removed = categorize_users(self.event.user, self.event.event, self.event.source_node,
                                                self.event.event, self.event.node)
        assert_equal({'email_transactional': [], 'email_digest': [], 'none': []}, warn)
        assert_equal({'email_transactional': [self.user_3._id], 'email_digest': [], 'none': []}, moved)

    def test_remove_user(self):
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.file_sub.email_transactional.append(self.user_3)
        self.file_sub.save()
        moved, warn, removed = categorize_users(self.event.user, self.event.event, self.event.source_node,
                                                self.event.event, self.event.node)
        assert_equal({'email_transactional': [self.user_3._id], 'email_digest': [], 'none': []}, removed)

    def tearDown(self):
        pass

wb_path = u'5581cb50a24f710b0f4623f9'
materialized = u'/One/Paper13.txt'
provider = u'osfstorage'
name = u'Paper13.txt'


file_payload = OrderedDict([
    (u'action', u'update'),
    (u'auth', OrderedDict([
        (u'email', u'tgn6m@osf.io'), (u'id', u'tgn6m'), (u'name', u'aab')])),
    (u'metadata', OrderedDict([
        (u'contentType', None),
        (u'etag', u'10485efa4069bb94d50588df2e7466a079d49d4f5fd7bf5b35e7c0d5b12d76b7'),
        (u'extra', OrderedDict([
            (u'downloads', 0),
            (u'version', 30)])),
        (u'kind', u'file'),
        (u'materialized', materialized),
        (u'modified', u'Wed, 24 Jun 2015 10:45:01 '),
        (u'name', name),
        (u'path', wb_path),
        (u'provider', provider),
        (u'size', 2008)])),
    (u'provider', provider),
    (u'time', 1435157161.979904)])

file_deleted_payload = OrderedDict([
    (u'action', u'delete'),
    (u'auth', OrderedDict([
        (u'email', u'tgn6m@osf.io'), (u'id', u'tgn6m'), (u'name', u'aab')])),
    (u'metadata', OrderedDict([
        (u'materialized', materialized),
        (u'path', materialized)])),  # Deleted files don't get wb_paths
    (u'provider', u'osfstorage'),
    (u'time', 1435157876.690203)])

folder_created_payload = OrderedDict([
    (u'action', u'create_folder'),
    (u'auth', OrderedDict([
        (u'email', u'tgn6m@osf.io'), (u'id', u'tgn6m'), (u'name', u'aab')])),
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
            (u'email', 'Bob'), (u'id', 'bob2'), (u'name', 'Bob')])),
        (u'destination', OrderedDict([
            (u'contentType', None),
            (u'etag', u'10485efa4069bb94d50588df2e7466a079d49d4f5fd7bf5b35e7c0d5b12d76b7'),
            (u'extra', OrderedDict([
                (u'downloads', 0),
                (u'version', 30)])),
            (u'kind', u'file'),
            (u'materialized', materialized),
            (u'modified', None),
            (u'name', name),
            (u'nid', str(new_node)),
            (u'path', wb_path),
            (u'provider', provider),
            (u'size', 2008),
            ('url', '/project/nhgts/files/osfstorage/5581cb50a24f710b0f4623f9/'),
            ('node', {'url': '/{}/'.format(new_node._id), '_id': new_node._id, 'title': u'Consolidate2'}),
            ('addon', 'OSF Storage')])),
        (u'source', OrderedDict([
            (u'materialized', materialized),
            (u'name', u'Paper13.txt'),
            (u'nid', str(old_node)),
            (u'path', materialized),  # Not wb path
            (u'provider', provider),
            ('url', '/project/nhgts/files/osfstorage/One/Paper13.txt/'),
            ('node', {'url': '/{}/'.format(old_node._id), '_id': old_node._id, 'title': u'Consolidate'}),
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

