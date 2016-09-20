from tests.base import OsfTestCase
from framework.auth import Auth
from tests.factories import UserFactory, PublicFilesFactory
from website.exceptions import NodeStateError
from website.util.permissions import WRITE
from website.public_files import give_user_public_files_node
from nose.tools import *  # noqa (PEP8 asserts)

class TestPublicFiles(OsfTestCase):
    def setUp(self):
        super(TestPublicFiles, self).setUp()
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = PublicFilesFactory(creator=self.user)

    def tearDown(self):
        super(TestPublicFiles, self).tearDown()
        self.project.remove()

    def test_normal_node_methods_disabled(self):
        user = UserFactory()

        with assert_raises(NodeStateError):
            self.project.set_title('Look at me: I\'m the title now',auth=self.auth)
            self.project.remove_node(auth=self.auth)
            self.project.fork_node(auth=self.auth)
            self.project.add_permission(user, WRITE)
            self.project.remove_permission(user, WRITE)
            self.project.remove_contributor(self.user, auth=self.auth)
            self.project.add_contributor(contributor=user,permissions=WRITE, auth=Auth(user))
            self.project.set_privacy(permissions='private', auth=self.auth)
            self.project.add_citation(self.auth)
            self.project.edit_citation(self.auth,{})
            self.project.remove_citation(self.auth,{})
            self.project.register_node(
                auth=self.auth
            )

    def test_user_merge_with_other_public_files_node(self):
        old_account = UserFactory()
        project = PublicFilesFactory(creator=old_account)
        self.project.get_addon('osfstorage').get_root().append_file('same')
        project.get_addon('osfstorage').get_root().append_file('same')
        with assert_raises(BaseException):
            self.user.merge_user(old_account)

        project.get_addon('osfstorage').get_root().delete()
        self.user.merge_user(old_account)
        assert len(self.project.get_addon('osfstorage').get_root().children) == 1
        assert self.project.get_addon('osfstorage').get_root().children[0].name == 'same'

    def test_give_user_public_files_node(self):
        user = UserFactory()
        give_user_public_files_node(user)

        assert user.public_files_node.is_public_files_node
        assert user.public_files_node.is_public