from nose.tools import *  # noqa

from faker import Factory
fake = Factory.create()
import uuid

from scripts.dropbox import migrate_to_external_accounts as migration

from framework.mongo import database

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

from website.models import User, Node
from website.oauth.models import ExternalAccount
from website.addons.dropbox.model import (
    DropboxUserSettings,
    DropboxNodeSettings
)

def fake_user_settings_document(user, deleted=False):
    return {
        "_id": fake.credit_card_number(),
        "_version": 1,
        "access_token": fake.sha1(),
        "deleted": deleted,
        "dropbox_id": fake.ean8(),
        "dropbox_info": {
            "display_name": fake.name()
        },
        "owner": user._id,
    }

def fake_node_settings_document(user_settings_document=None, node=None, deleted=False):
    return {
        "_id": fake.credit_card_number(),
        "_version": 1,
        "deleted": deleted,
        "folder": uuid.uuid4(),
        "owner": node._id if node else 'null',
        "user_settings": user_settings_document['_id'] if user_settings_document else 'null'
    }

class TestDropboxMigration(OsfTestCase):

    def setUp(self):
        super(TestDropboxMigration, self).setUp()
        self.unlinked_user_settings = []
        self.linked_user_settings = []
        self.deleted_user_settings = []
        self.node_settings_documents = []
        self.unauthorized_node_settings_documents = []
        for i in range(3):
            user = UserFactory()
            self.unlinked_user_settings.append(fake_user_settings_document(user))
        database['dropboxusersettings'].insert(self.unlinked_user_settings)
        for i in range(3):
            user = UserFactory()
            self.linked_user_settings.append(fake_user_settings_document(user))
            node = ProjectFactory()
            self.node_settings_documents.append(
                fake_node_settings_document(self.linked_user_settings[-1], node)
            )
        database['dropboxusersettings'].insert(self.linked_user_settings)
        database['dropboxnodesettings'].insert(self.node_settings_documents)
        for i in range(3):
            user = UserFactory()
            self.deleted_user_settings.append(fake_user_settings_document(user, deleted=True))
        database['dropboxusersettings'].insert(self.deleted_user_settings)
        for i in range(3):
            node = ProjectFactory()
            self.unauthorized_node_settings_documents.append(
                fake_node_settings_document(None, node)
            )
        database['dropboxnodesettings'].insert(self.unauthorized_node_settings_documents)

    def tearDown(self):
        super(TestDropboxMigration, self).tearDown()
        database['dropboxnodesettings'].remove()
        database['dropboxusersettings'].remove()
        database['externalaccount'].remove()

    def test_migrate_to_external_account(self):
        assert_equal(ExternalAccount.find().count(), 0)
        user_settings_document = self.unlinked_user_settings[0]
        external_account, user, new = migration.migrate_to_external_account(user_settings_document)
        assert_true(new)
        assert_equal(ExternalAccount.find().count(), 1)
        assert_is_not_none(external_account)
        assert_equal(user_settings_document['owner'], user._id)
        assert_equal(external_account.provider, 'dropbox')
        assert_equal(external_account.provider_name, 'Dropbox')
        assert_equal(
            external_account.oauth_key,
            user_settings_document['access_token']
        )
        assert_equal(
            external_account.display_name,
            user_settings_document['dropbox_info']['display_name']
        )

    def test_make_new_user_settings(self):
        user_settings_document = self.unlinked_user_settings[0]
        user = User.load(user_settings_document['owner'])
        user_settings = migration.make_new_user_settings(user)
        user.reload()
        assert_equal(
            len(user._backrefs['addons']['dropboxusersettings']['owner']),
            1
        )
        assert_equal(
            user._backrefs['addons']['dropboxusersettings']['owner'][0],
            user_settings._id
        )
        assert_false(hasattr(user_settings, 'access_token'))

    def test_make_new_node_settings(self):
        node_settings_document = self.node_settings_documents[0]
        node = Node.load(node_settings_document['owner'])
        user_settings_document = database['dropboxusersettings'].find_one({
            '_id':  node_settings_document['user_settings']
        })
        external_account, user, new = migration.migrate_to_external_account(
            user_settings_document
        )
        user_settings = migration.make_new_user_settings(user)
        node_settings = migration.make_new_node_settings(
            node,
            node_settings_document,
            external_account,
            user_settings
        )
        assert_equal(
            len(node._backrefs['addons']['dropboxnodesettings']['owner']),
            1
        )
        assert_equal(
            node._backrefs['addons']['dropboxnodesettings']['owner'][0],
            node_settings._id
        )

    def test_remove_old_documents(self):
        user_settings_collection = database['dropboxusersettings']
        old_user_settings = list(user_settings_collection.find())
        old_user_settings_count = user_settings_collection.count()
        node_settings_collection = database['dropboxnodesettings']
        old_node_settings = list(node_settings_collection.find())
        old_node_settings_count = node_settings_collection.count
        migration.migrate(dry_run=False, remove_old=False)
        assert_equal(
            database['dropboxusersettings'].count(),
            15
        )  # 3 + 3 + 3 + 6 (non-deleted)
        assert_equal(
            database['dropboxnodesettings'].count(),
            9
        )  # 3 + 3 + 3
        migration.remove_old_documents(
            old_user_settings, old_user_settings_count,
            old_node_settings, old_node_settings_count,
            dry_run=False
        )
        assert_equal(
            database['dropboxusersettings'].count(),
            6
        )
        assert_equal(
            database['dropboxnodesettings'].count(),
            3
        )

    def test_migrate(self):
        migration.migrate(dry_run=False)
        assert_equal(
            DropboxUserSettings.find().count(),
            6
        )
        assert_equal(
            DropboxNodeSettings.find().count(),
            3
        )
        for user_settings in DropboxUserSettings.find():
            assert_is_not_none(user_settings.owner)
            assert_false(hasattr(user_settings, 'access_token'))
        for node_settings in DropboxNodeSettings.find():
            assert_is_not_none(node_settings.owner)
            if (
                    not node_settings.user_settings or
                    not node_settings.external_account
            ):
                assert_in(
                    node_settings.folder,
                    map(
                        lambda d: d['folder'],
                        self.unauthorized_node_settings_documents
                    )
                )

    def test_migrate_two_users_one_account(self):
        self.linked_user_settings[1]["_id"] = self.linked_user_settings[0]["_id"]
        self.linked_user_settings[1]["_version"] = self.linked_user_settings[0]["_version"]
        self.linked_user_settings[1]["access_token"] = self.linked_user_settings[0]["access_token"]
        self.linked_user_settings[1]["deleted"] = self.linked_user_settings[0]["deleted"]
        self.linked_user_settings[1]["dropbox_id"] = self.linked_user_settings[0]["dropbox_id"]
        self.linked_user_settings[1]["dropbox_info"] = self.linked_user_settings[0]["dropbox_info"]

        external_account_1, user_1, new_1 = migration.migrate_to_external_account(self.linked_user_settings[0])
        external_account_2, user_2, new_2 = migration.migrate_to_external_account(self.linked_user_settings[1])

        assert_equal(external_account_1._id, external_account_2._id)
        assert_not_equal(user_1, user_2)
        assert_true(new_1)
        assert_false(new_2)
