from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType

from osf.models import NotificationType
from tests.utils import capture_notifications
from notifications.file_event_notifications import  (
    event_registry,
    FileAdded,
    FileRemoved,
    FolderCreated,
    FileUpdated,
    AddonFileCopied,
    AddonFileMoved,
    AddonFileRenamed,
)
from framework.auth import Auth
from osf_tests import factories
from osf.utils.permissions import WRITE
from tests.base import OsfTestCase

email_transactional = 'email_transactional'
email_digest = 'email_digest'



class TestListOfFiles(OsfTestCase):
    """
    List files given a list
    """
    def setUp(self):
        super().setUp()
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


class TestEventExists(OsfTestCase):
    # Add all possible called events here to ensure that the Event class can
    #  call them.
    def setUp(self):
        super().setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.node = factories.ProjectFactory(creator=self.user)

    def test_get_file_updated(self):
        # Event gets FileUpdated from file_updated
        event = event_registry['file_updated'](self.user, self.node, 'file_updated', payload=file_payload)
        assert isinstance(event, FileUpdated)

    def test_get_file_added(self):
        # Event gets FileAdded from file_added
        event = event_registry['file_added'](self.user, self.node, 'file_added', payload=file_payload)
        assert isinstance(event, FileAdded)

    def test_get_file_removed(self):
        # Event gets FileRemoved from file_removed
        event = event_registry['file_removed'](self.user, self.node, 'file_removed', payload=file_deleted_payload)
        assert isinstance(event, FileRemoved)

    def test_get_folder_created(self):
        # Event gets FolderCreated from folder_created
        event = event_registry['folder_created'](self.user, self.node, 'folder_created', payload=folder_created_payload)
        assert isinstance(event, FolderCreated)

    def test_get_file_moved(self):
        # Event gets AddonFileMoved from addon_file_moved
        file_moved_payload = file_move_payload(self.node, self.node)
        event = event_registry['addon_file_moved'](self.user, self.node, 'addon_file_moved', payload=file_moved_payload)
        assert isinstance(event, AddonFileMoved)

    def test_get_file_copied(self):
        # Event gets AddonFileCopied from addon_file_copied
        file_copied_payload = file_copy_payload(self.node, self.node)
        event = event_registry['addon_file_copied'](self.user, self.node, 'addon_file_copied',
                                                    payload=file_copied_payload)
        assert isinstance(event, AddonFileCopied)

    def test_get_file_renamed(self):
        # Event gets AddonFileCopied from addon_file_copied
        file_rename_payload = file_renamed_payload()
        event = event_registry['addon_file_renamed'](self.user, self.node, 'addon_file_renamed',
                                                     payload=file_rename_payload)
        assert isinstance(event, AddonFileRenamed)


class TestFileUpdated(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user_1 = factories.AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.user_2 = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user_1)
        # subscription
        self.sub = factories.NotificationSubscriptionFactory(
            object_id=self.project.id,
            content_type=ContentType.objects.get_for_model(self.project),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED)
        )
        self.sub.save()
        self.event = event_registry['file_updated'](self.user_2, self.project, 'file_updated', payload=file_payload)

    def test_info_formed_correct(self):
        assert f'{wb_path}_file_updated' == self.event.event_type
        assert f'updated file "<b>{materialized.lstrip("/")}</b>".' == self.event.html_message
        assert f'updated file "{materialized.lstrip("/")}".' == self.event.text_message

    def test_file_updated(self):
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.FILE_UPDATED


class TestFileAdded(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            object_id=self.project.id,
            content_type=ContentType.objects.get_for_model(self.project),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED)
        )
        self.project_subscription.save()
        self.user2 = factories.UserFactory()
        self.event = event_registry['file_added'](self.user2, self.project, 'file_added', payload=file_payload)

    def test_info_formed_correct(self):
        assert f'{wb_path}_file_updated' == self.event.event_type
        assert f'added file "<b>{materialized.lstrip("/")}</b>".' == self.event.html_message
        assert f'added file "{materialized.lstrip("/")}".' == self.event.text_message

    def test_file_added(self):
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.FILE_ADDED


class TestFileRemoved(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            object_id=self.project.id,
            content_type=ContentType.objects.get_for_model(self.project),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_REMOVED)
        )
        self.project_subscription.object_id = self.project.id
        self.project_subscription.content_type = ContentType.objects.get_for_model(self.project)
        self.project_subscription.save()
        self.user2 = factories.UserFactory()
        self.event = event_registry['file_removed'](
            self.user2, self.project, 'file_removed', payload=file_deleted_payload
        )

    def test_info_formed_correct_file(self):
        assert NotificationType.Type.FILE_UPDATED == self.event.event_type
        assert f'removed file "<b>{materialized.lstrip("/")}</b>".' == self.event.html_message
        assert f'removed file "{materialized.lstrip("/")}".' == self.event.text_message

    def test_info_formed_correct_folder(self):
        assert NotificationType.Type.FILE_UPDATED == self.event.event_type
        self.event.payload['metadata']['materialized'] += '/'
        assert f'removed folder "<b>{materialized.lstrip("/")}/</b>".' == self.event.html_message
        assert f'removed folder "{materialized.lstrip("/")}/".' == self.event.text_message

    def test_file_removed(self):
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.FILE_REMOVED


class TestFolderCreated(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            user=self.user,
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED),
        )
        self.project_subscription.save()
        self.user2 = factories.UserFactory()
        self.event = event_registry['folder_created'](
            self.user2, self.project, 'folder_created', payload=folder_created_payload
        )

    def test_info_formed_correct(self):
        assert NotificationType.Type.FILE_UPDATED == self.event.event_type
        assert 'created folder "<b>Three/</b>".' == self.event.html_message
        assert 'created folder "Three/".' == self.event.text_message

    def test_folder_added(self):
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.FOLDER_CREATED


class TestFolderFileRenamed(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user_1 = factories.AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.user_2 = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user_1)
        # subscription
        self.sub = factories.NotificationSubscriptionFactory(
            user=self.user_2,
            object_id=self.project.id,
            content_type=ContentType.objects.get_for_model(self.project),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED)
        )
        self.sub.save()

        # Payload
        file_renamed_payload = file_move_payload(self.project, self.project)
        self.event = event_registry['addon_file_renamed'](
            self.user_1, self.project, 'addon_file_renamed',
            payload=file_renamed_payload
        )
        self.sub.save()

    def test_rename_file_html(self):
        self.event.payload['destination']['materialized'] = '/One/Paper14.txt'
        assert self.event.html_message == 'renamed file "<b>/One/Paper13.txt</b>" to "<b>/One/Paper14.txt</b>".'

    def test_rename_folder_html(self):
        self.event.payload['destination']['kind'] = 'folder'
        self.event.payload['destination']['materialized'] = '/One/Two/Four'
        self.event.payload['source']['materialized'] = '/One/Two/Three'
        assert self.event.html_message == 'renamed folder "<b>/One/Two/Three</b>" to "<b>/One/Two/Four</b>".'

    def test_rename_file_text(self):
        self.event.payload['destination']['materialized'] = '/One/Paper14.txt'
        assert self.event.text_message == 'renamed file "/One/Paper13.txt" to "/One/Paper14.txt".'

    def test_rename_folder_text(self):
        self.event.payload['destination']['kind'] = 'folder'
        self.event.payload['destination']['materialized'] = '/One/Two/Four'
        self.event.payload['source']['materialized'] = '/One/Two/Three'
        assert self.event.text_message == 'renamed folder "/One/Two/Three" to "/One/Two/Four".'


class TestFileMoved(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user_1 = factories.AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.user_2 = factories.AuthUserFactory()
        self.user_3 = factories.AuthUserFactory()
        self.user_4 = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user_1)
        self.private_node = factories.NodeFactory(parent=self.project, is_public=False, creator=self.user_1)
        # Payload
        file_moved_payload = file_move_payload(self.private_node, self.project)
        self.event = event_registry['addon_file_moved'](
            self.user_2, self.private_node, 'addon_file_moved', payload=file_moved_payload
        )
        # Subscriptions
        # for parent node
        self.sub = factories.NotificationSubscriptionFactory(
            object_id=self.project.id,
            content_type=ContentType.objects.get_for_model(self.project),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED)
        )
        self.sub.save()
        # for private node
        self.private_sub = factories.NotificationSubscriptionFactory(
            object_id=self.private_node.id,
            content_type=ContentType.objects.get_for_model(self.private_node),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED)
        )
        self.private_sub.save()
        # for file subscription
        self.file_sub = factories.NotificationSubscriptionFactory(
            object_id=self.project.id,
            content_type=ContentType.objects.get_for_model(self.project),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.NODE_FILES_UPDATED)
        )
        self.file_sub.save()

    def test_info_formed_correct(self):
        # Move Event: Ensures data is correctly formatted
        assert f'{wb_path}_file_updated' == self.event.event_type
        # assert 'moved file "<b>{}</b>".' == self.event.html_message
        # assert 'created folder "Three/".' == self.event.text_message

    def test_user_performing_action_no_email(self):
        # Move Event: Makes sure user who performed the action is not
        # included in the notifications
        self.sub.user = self.user_2
        self.sub.save()
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.ADDON_FILE_MOVED
        assert notifications['emits'][0]['kwargs']['user'] == self.user_2

    def test_perform_store_called_once(self):
        self.sub.user = self.user_1
        self.sub.save()
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.ADDON_FILE_MOVED

    def test_perform_store_one_of_each(self):
        # Move Event: Tests that store_emails is called 3 times, one in
        # each category
        self.sub.user = self.user_1
        self.sub.save()
        self.project.add_contributor(self.user_3, permissions=WRITE, auth=self.auth)
        self.project.save()
        self.private_node.add_contributor(self.user_3, permissions=WRITE, auth=self.auth)
        self.private_node.save()
        self.sub.user = self.user_3
        self.sub.save()
        self.project.add_contributor(self.user_4, permissions=WRITE, auth=self.auth)
        self.project.save()
        self.sub.user = self.user_4
        self.sub.save()
        self.file_sub.save()
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.ADDON_FILE_MOVED

    def test_remove_user_sent_once(self):
        # Move Event: Tests removed user is removed once. Regression
        self.project.add_contributor(self.user_3, permissions=WRITE, auth=self.auth)
        self.project.save()
        self.file_sub.user = self.user_3
        self.file_sub.save()
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.ADDON_FILE_MOVED


class TestFileCopied(OsfTestCase):
    # Test the copying of files
    def setUp(self):
        super().setUp()
        self.user_1 = factories.AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.user_2 = factories.AuthUserFactory()
        self.user_3 = factories.AuthUserFactory()
        self.user_4 = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user_1)
        self.private_node = factories.NodeFactory(parent=self.project, is_public=False, creator=self.user_1)
        # Payload
        file_copied_payload = file_copy_payload(self.private_node, self.project)
        self.event = event_registry['addon_file_copied'](
            self.user_2, self.private_node, 'addon_file_copied',
            payload=file_copied_payload
        )
        # Subscriptions
        # for parent node
        self.sub = factories.NotificationSubscriptionFactory(
            object_id=self.project.id,
            content_type=ContentType.objects.get_for_model(self.project),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED)
        )
        self.sub.save()
        # for private node
        self.private_sub = factories.NotificationSubscriptionFactory(
            object_id=self.private_node.id,
            content_type=ContentType.objects.get_for_model(self.private_node),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED)
        )
        self.private_sub.save()
        # for file subscription
        self.file_sub = factories.NotificationSubscriptionFactory(
            object_id=self.project.id,
            content_type=ContentType.objects.get_for_model(self.project),
            notification_type=NotificationType.objects.get(name=NotificationType.Type.NODE_FILES_UPDATED)
        )
        self.file_sub.save()

    def test_info_correct(self):
        # Move Event: Ensures data is correctly formatted
        assert f'{wb_path}_file_updated' == self.event.event_type
        assert ('copied file "<b>One/Paper13.txt</b>" from OSF Storage'
                      ' in Consolidate to "<b>Two/Paper13.txt</b>" in OSF'
                      ' Storage in Consolidate.') == self.event.html_message
        assert ('copied file "One/Paper13.txt" from OSF Storage'
                      ' in Consolidate to "Two/Paper13.txt" in OSF'
                      ' Storage in Consolidate.') == self.event.text_message

    def test_copied_one_of_each(self):
        # Copy Event: Tests that emit is called 2 times, two with
        # permissions, one without
        self.sub.user = self.user_1
        self.sub.save()
        self.project.add_contributor(self.user_3, permissions=WRITE, auth=self.auth)
        self.project.save()
        self.private_node.add_contributor(self.user_3, permissions=WRITE, auth=self.auth)
        self.private_node.save()
        self.sub.user = self.user_3
        self.sub.save()
        self.project.add_contributor(self.user_4, permissions=WRITE, auth=self.auth)
        self.project.save()
        self.file_sub.user = self.user_4
        self.file_sub.save()
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.ADDON_FILE_COPIED

    def test_user_performing_action_no_email(self):
        # Move Event: Makes sure user who performed the action is not
        # included in the notifications
        self.sub.user = self.user_2
        self.sub.save()
        with capture_notifications() as notifications:
            self.event.perform()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.ADDON_FILE_COPIED


class TestSubscriptionManipulations(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.emails_1 = {
            email_digest: ['a1234', 'b1234', 'c1234'],
            email_transactional: ['d1234', 'e1234', 'f1234'],
            'none': ['g1234', 'h1234', 'i1234']
        }
        self.emails_2 = {
            email_digest: ['j1234'],
            email_transactional: ['k1234'],
            'none': ['l1234']
        }
        self.emails_3 = {
            email_digest: ['b1234', 'c1234'],
            email_transactional: ['e1234', 'f1234'],
            'none': ['h1234', 'i1234']
        }
        self.emails_4 = {
            email_digest: ['d1234', 'i1234'],
            email_transactional: ['b1234'],
            'none': []
        }
        self.diff_1_3 = {email_transactional: ['d1234'], 'none': ['g1234'], email_digest: ['a1234']}
        self.union_1_2 = {'email_transactional': ['e1234', 'f1234', 'd1234', 'k1234'],
                          'none': ['h1234', 'g1234', 'i1234', 'l1234'],
                          'email_digest': ['j1234', 'a1234', 'c1234', 'b1234']}
        self.dup_1_3 = {email_transactional: ['e1234', 'f1234'], 'none': ['h1234', 'g1234'],
                        'email_digest': ['a1234', 'c1234']}


wb_path = '5581cb50a24f710b0f4623f9'
materialized = '/One/Paper13.txt'
provider = 'osfstorage'
name = 'Paper13.txt'


file_payload = OrderedDict([
    ('action', 'update'),
    ('auth', OrderedDict([
        ('email', 'tgn6m@osf.io'), ('id', 'tgn6m'), ('name', 'aab')])),
    ('metadata', OrderedDict([
        ('contentType', None),
        ('etag', '10485efa4069bb94d50588df2e7466a079d49d4f5fd7bf5b35e7c0d5b12d76b7'),
        ('extra', OrderedDict([
            ('downloads', 0),
            ('version', 30)])),
        ('kind', 'file'),
        ('materialized', materialized),
        ('modified', 'Wed, 24 Jun 2015 10:45:01 '),
        ('name', name),
        ('path', wb_path),
        ('provider', provider),
        ('size', 2008)])),
    ('provider', provider),
    ('time', 1435157161.979904)])

file_deleted_payload = OrderedDict([
    ('action', 'delete'),
    ('auth', OrderedDict([
        ('email', 'tgn6m@osf.io'), ('id', 'tgn6m'), ('name', 'aab')])),
    ('metadata', OrderedDict([
        ('materialized', materialized),
        ('path', materialized)])),  # Deleted files don't get wb_paths
    ('provider', 'osfstorage'),
    ('time', 1435157876.690203)])

folder_created_payload = OrderedDict([
    ('action', 'create_folder'),
    ('auth', OrderedDict([
        ('email', 'tgn6m@osf.io'), ('id', 'tgn6m'), ('name', 'aab')])),
    ('metadata', OrderedDict([
        ('etag', '5caf8ab73c068565297e455ebce37fd64b6897a2284ec9d7ecba8b6093082bcd'),
        ('extra', OrderedDict()),
        ('kind', 'folder'),
        ('materialized', '/Three/'),
        ('name', 'Three'),
        ('path', '558ac595a24f714eff336d66/'),
        ('provider', 'osfstorage')])),
    ('provider', 'osfstorage'),
    ('time', 1435157969.475282)])


def file_move_payload(new_node, old_node):
    return OrderedDict([
        ('action', 'move'),
        ('auth', OrderedDict([
            ('email', 'Bob'), ('id', 'bob2'), ('name', 'Bob')])),
        ('destination', OrderedDict([
            ('contentType', None),
            ('etag', '10485efa4069bb94d50588df2e7466a079d49d4f5fd7bf5b35e7c0d5b12d76b7'),
            ('extra', OrderedDict([
                ('downloads', 0),
                ('version', 30)])),
            ('kind', 'file'),
            ('materialized', materialized),
            ('modified', None),
            ('name', name),
            ('nid', str(new_node)),
            ('path', wb_path),
            ('provider', provider),
            ('size', 2008),
            ('url', '/project/nhgts/files/osfstorage/5581cb50a24f710b0f4623f9/'),
            ('node', {'url': f'/{new_node._id}/', '_id': new_node._id, 'title': 'Consolidate2'}),
            ('addon', 'OSF Storage')])),
        ('source', OrderedDict([
            ('materialized', materialized),
            ('name', 'Paper13.txt'),
            ('nid', str(old_node)),
            ('path', materialized),  # Not wb path
            ('provider', provider),
            ('url', '/project/nhgts/files/osfstorage/One/Paper13.txt/'),
            ('node', {'url': f'/{old_node._id}/', '_id': old_node._id, 'title': 'Consolidate'}),
            ('addon', 'OSF Storage')])),
        ('time', 1435158051.204264),
        ('node', 'nhgts'),
        ('project', None)])


def file_copy_payload(new_node, old_node):
    return OrderedDict([
        ('action', 'copy'),
        ('auth', OrderedDict([
            ('email', 'tgn6m@osf.io'),
            ('id', 'tgn6m'),
            ('name', 'aab')])),
        ('destination', OrderedDict([
            ('contentType', None),
            ('etag', '16075ae3e546971003095beef8323584de40b1fcbf52ed4bb9e7f8547e322824'),
            ('extra', OrderedDict([
                ('downloads', 0),
                ('version', 30)])),
            ('kind', 'file'),
            ('materialized', 'Two/Paper13.txt'),
            ('modified', None),
            ('name', 'Paper13.txt'),
            ('nid', 'nhgts'),
            ('path', wb_path),
            ('provider', 'osfstorage'),
            ('size', 2008),
            ('url', '/project/nhgts/files/osfstorage/558ac45da24f714eff336d59/'),
            ('node', {'url': '/nhgts/', '_id': old_node._id, 'title': 'Consolidate'}),
            ('addon', 'OSF Storage')])),
        ('source', OrderedDict([
            ('materialized', 'One/Paper13.txt'),
            ('name', 'Paper13.txt'),
            ('nid', 'nhgts'),
            ('path', 'One/Paper13.txt'),
            ('provider', 'osfstorage'),
            ('url', '/project/nhgts/files/osfstorage/One/Paper13.txt/'),
            ('node', {'url': '/nhgts/', '_id': new_node._id, 'title': 'Consolidate'}),
            ('addon', 'OSF Storage')])),
        ('time', 1435157658.036183),
        ('node', 'nhgts'),
        ('project', None)])


def file_renamed_payload():
    return OrderedDict([
        ('action', 'move'),
        ('auth', OrderedDict([
            ('email', 'tgn6m@osf.io'),
            ('id', 'tgn6m'),
            ('name', 'aab')])),
        ('destination', OrderedDict([
            ('contentType', None),
            ('etag', '0e9bfddcb5a59956ae60e93f32df06b174ad33b53d8a2f2cd08c780cf34a9d93'),
            ('extra', OrderedDict([
                ('downloads', 0),
                ('hashes', OrderedDict([
                    ('md5', '79a64594dd446674ce1010007ac2bde7'),
                    ('sha256', 'bf710301e591f6f5ce35aa8971cfc938b39dae0fedcb9915656dded6ad025580')])),
                ('version', 1)])),
            ('kind', 'file'),
            ('materialized', 'Fibery/file2.pdf'),
            ('modified', '2015-05-07T10:54:32'),
            ('name', 'file2.pdf'),
            ('nid', 'wp6xv'),
            ('path', '/55f07134a24f71b2a24f4812'),
            ('provider', 'osfstorage'),
            ('size', 21209),
            ('url', '/project/wp6xv/files/osfstorage/55f07134a24f71b2a24f4812/'),
            ('node', {'url': '/wp6xv/', '_id': 'wp6xv', 'title': 'File_Notify4'}),
            ('addon', 'OSF Storage')])),
        ('source', OrderedDict([
            ('materialized', 'Fibery/!--i--2.pdf'),
            ('name', '!--i--2.pdf'), ('nid', 'wp6xv'),
            ('path', 'Fibery/!--i--2.pdf'),
            ('provider', 'osfstorage'),
            ('url', '/project/wp6xv/files/osfstorage/Fibery/%21--i--2.pdf/'),
            ('node', {'url': '/wp6xv/', '_id': 'wp6xv', 'title': 'File_Notify4'}),
            ('addon', 'OSF Storage')])),
        ('time', 1441905340.876648),
        ('node', 'wp6xv'),
        ('project', None)])
