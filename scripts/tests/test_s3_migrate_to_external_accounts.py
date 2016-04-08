import mock
from nose.tools import *  # noqa

from faker import Factory
fake = Factory.create()
import uuid

from scripts.s3 import migrate_to_external_accounts as migration

from framework.mongo import database

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

from website.models import User, Node
from website.oauth.models import ExternalAccount
from website.addons.s3.model import (
    S3UserSettings,
    S3NodeSettings
)

class fake_user_info(object):
    def __init__(self, id=None, display_name=None):
        self.id = id or fake.credit_card_number()
        self.display_name = display_name or fake.name()

def fake_user_settings_document(user, deleted=False):
    return {
        "_id": fake.credit_card_number(),
        "_version": 1,
        "access_key": fake.sha1(),
        "secret_key": fake.sha1(),
        "deleted": deleted,
        "owner": user._id,
    }

def fake_node_settings_document(user_settings_document=None, node=None, deleted=False, encrypt_uploads=True):
    ret = {
        "_id": fake.credit_card_number(),
        "_version": 1,
        "deleted": deleted,
        "bucket": uuid.uuid4(),
        "owner": node._id if node else 'null',
        "user_settings": user_settings_document['_id'] if user_settings_document else 'null'
    }
    if encrypt_uploads:
        ret.update({
            "encrypt_uploads": True,
        })
    return ret

class TestS3Migration(OsfTestCase):

    def setUp(self):
        super(TestS3Migration, self).setUp()
        self.mock_user_info = mock.patch('scripts.s3.migrate_to_external_accounts.utils.get_user_info', 
            mock.PropertyMock(return_value=fake_user_info()))
        self.mock_user_info.start()
        self.unlinked_user_settings = []
        self.linked_user_settings = []
        self.deleted_user_settings = []
        self.node_settings_documents = []
        self.unauthorized_node_settings_documents = []
        self.node_settings_no_encrypt = []
        for i in range(3):
            user = UserFactory()
            self.unlinked_user_settings.append(fake_user_settings_document(user))
        database['addons3usersettings'].insert(self.unlinked_user_settings)
        for i in range(3):
            user = UserFactory()
            self.linked_user_settings.append(fake_user_settings_document(user))
            node = ProjectFactory()
            self.node_settings_documents.append(
                fake_node_settings_document(self.linked_user_settings[-1], node)
            )
        database['addons3usersettings'].insert(self.linked_user_settings)
        database['addons3nodesettings'].insert(self.node_settings_documents)
        for i in range(3):
            user = UserFactory()
            self.deleted_user_settings.append(fake_user_settings_document(user, deleted=True))
        database['addons3usersettings'].insert(self.deleted_user_settings)
        for i in range(3):
            node = ProjectFactory()
            self.unauthorized_node_settings_documents.append(
                fake_node_settings_document(None, node)
            )
        database['addons3nodesettings'].insert(self.unauthorized_node_settings_documents)
        self.node_settings_no_encrypt.append(
            fake_node_settings_document(self.linked_user_settings[-1], node, encrypt_uploads=False)
        )
        database['addons3nodesettings'].insert(self.node_settings_no_encrypt)

    def tearDown(self):
        self.mock_user_info.stop()
        super(TestS3Migration, self).tearDown()
        database['addons3nodesettings'].remove()
        database['addons3usersettings'].remove()
        database['s3nodesettings'].remove()
        database['s3usersettings'].remove()
        database['externalaccount'].remove()

    def test_migrate_to_external_account(self):
        assert_equal(ExternalAccount.find().count(), 0)
        user_settings_document = self.unlinked_user_settings[0]
        external_account, user, new = migration.migrate_to_external_account(user_settings_document)
        assert_true(new)
        assert_equal(ExternalAccount.find().count(), 1)
        assert_is_not_none(external_account)
        assert_equal(user_settings_document['owner'], user._id)
        assert_equal(external_account.provider, 's3')
        assert_equal(external_account.provider_name, 'Amazon S3')
        assert_equal(
            external_account.oauth_key,
            user_settings_document['access_key']
        )
        assert_is_not_none(external_account.display_name)

    def test_make_new_user_settings(self):
        user_settings_document = self.unlinked_user_settings[0]
        user = User.load(user_settings_document['owner'])
        user_settings = migration.make_new_user_settings(user)
        user.reload()
        assert(
            'addons3usersettings' not in user._backrefs['addons']
        )
        assert_equal(
            len(user._backrefs['addons']['s3usersettings']['owner']),
            1
        )
        assert_equal(
            user._backrefs['addons']['s3usersettings']['owner'][0],
            user_settings._id
        )
        assert_false(hasattr(user_settings, 'access_key'))

    def test_make_new_node_settings(self):
        node_settings_document = self.node_settings_documents[0]
        node = Node.load(node_settings_document['owner'])
        user_settings_document = database['addons3usersettings'].find_one({
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
        assert(
            'addons3nodesettings' not in node._backrefs['addons']
        )
        assert_equal(
            len(node._backrefs['addons']['s3nodesettings']['owner']),
            1
        )
        assert_equal(
            node._backrefs['addons']['s3nodesettings']['owner'][0],
            node_settings._id
        )

    def test_migrate(self):
        migration.migrate(dry_run=False)
        assert_equal(
            S3UserSettings.find().count(),
            len(self.linked_user_settings + self.unlinked_user_settings)
        )
        assert_equal(
            S3NodeSettings.find().count(),
            len(self.node_settings_documents + self.node_settings_no_encrypt)
        )
        for user_settings in S3UserSettings.find():
            assert_is_not_none(user_settings.owner)
            assert_false(hasattr(user_settings, 'access_key'))
        for node_settings in S3NodeSettings.find():
            assert_is_not_none(node_settings.owner)
            assert_is_not_none(node_settings.external_account)

    def test_migrate_two_users_one_account(self):
        self.mock_user_info.stop()
        self.mock_user_info.return_value = fake_user_info(id='1234567890', display_name='s3.user')
        self.mock_user_info.start()
        self.linked_user_settings[1]["_id"] = self.linked_user_settings[0]["_id"]
        self.linked_user_settings[1]["_version"] = self.linked_user_settings[0]["_version"]
        self.linked_user_settings[1]["access_key"] = self.linked_user_settings[0]["access_key"]
        self.linked_user_settings[1]["deleted"] = self.linked_user_settings[0]["deleted"]

        external_account_1, user_1, new_1 = migration.migrate_to_external_account(self.linked_user_settings[0])
        external_account_2, user_2, new_2 = migration.migrate_to_external_account(self.linked_user_settings[1])

        assert_equal(external_account_1._id, external_account_2._id)
        assert_not_equal(user_1, user_2)
        assert_true(new_1)
        assert_false(new_2)
