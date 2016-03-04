from api_tests.utils import create_test_file
from framework.guid.model import Guid
from scripts.migrate_comment_targets import update_comment_targets_to_guids
from tests.base import OsfTestCase
from tests.factories import CommentFactory, ProjectFactory
from nose.tools import *  # PEP8 asserts


class TestMigrateCommentsTargets(OsfTestCase):

    def setUp(self):
        super(TestMigrateCommentsTargets, self).setUp()
        self.project = ProjectFactory()

    def _set_up_comment_with_target(self, root_target, target):
        comment = CommentFactory(node=self.project)
        comment.root_target = root_target
        comment.target = target
        comment.save()
        return comment

    def test_migrate_file_root_comment(self):
        test_file = create_test_file(node=self.project, user=self.project.creator)
        comment = self._set_up_comment_with_target(root_target=test_file, target=test_file)
        update_comment_targets_to_guids()
        comment.reload()
        assert_equal(comment.root_target, test_file.get_guid())
        assert_equal(comment.target, test_file.get_guid())

    def test_migrate_project_root_comment(self):
        comment = self._set_up_comment_with_target(root_target=self.project, target=self.project)
        update_comment_targets_to_guids()
        comment.reload()
        assert_equal(comment.root_target, Guid.load(self.project._id))
        assert_equal(comment.target, Guid.load(self.project._id))

    def test_migrate_project_comment_reply(self):
        comment = self._set_up_comment_with_target(root_target=self.project, target=self.project)
        reply = self._set_up_comment_with_target(root_target=self.project, target=comment)
        update_comment_targets_to_guids()
        reply.reload()
        assert_equal(reply.root_target, Guid.load(self.project._id))
        assert_equal(reply.target, Guid.load(comment._id))

    def test_migrate_file_comment_reply(self):
        test_file = create_test_file(node=self.project, user=self.project.creator)
        comment = self._set_up_comment_with_target(root_target=test_file, target=test_file)
        reply = self._set_up_comment_with_target(root_target=test_file, target=comment)
        update_comment_targets_to_guids()
        reply.reload()
        assert_equal(reply.root_target, test_file.get_guid())
        assert_equal(reply.target, Guid.load(comment._id))
