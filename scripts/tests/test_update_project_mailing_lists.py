# -*- coding: utf-8 -*-

import mock

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory
from tests.factories import UserFactory
from tests.factories import AuthUserFactory

from framework.auth.core import Auth
from framework.exceptions import HTTPError

from scripts.update_project_mailing_lists import main, update_node


class TestUpdateProjectMailingLists(OsfTestCase):

    def setUp(self):
        super(TestUpdateProjectMailingLists, self).setUp()
        self.other_nodes = [ProjectFactory() for i in range(10)]
        self.creator = AuthUserFactory()
        self.node = ProjectFactory(creator=self.creator)

    @mock.patch('scripts.update_project_mailing_lists.full_update')
    def test_only_updated_project_is_checked(self, mock_full_update):
        self.node.mailing_updated = True
        self.node.save()

        main(dry_run=False)
        self.node.reload()

        mock_full_update.assert_called_with(self.node)
        assert_false(self.node.mailing_updated)

    def test_create_node_without_list_does_not_update(self):
        assert_false(self.node.mailing_updated)

    def test_create_node_with_list_causes_update(self):
        new_node = ProjectFactory(parent=None)

        assert_true(new_node.mailing_updated)

    def test_add_contributor_causes_update(self):
        user = UserFactory()
        self.node.add_contributor(user, save=True)

        self.node.reload()
        assert_true(self.node.mailing_updated)

    def test_remove_contributor_causes_update(self):
        user = UserFactory()
        self.node.add_contributor(user)
        self.node.mailing_updated = False
        self.node.save()
        self.node.remove_contributor(user, auth=Auth(self.creator), save=True)

        self.node.reload()
        assert_true(self.node.mailing_updated)

    def test_change_title_causes_update(self):
        self.node.set_title('New Title', Auth(self.creator), save=True)

        self.node.reload()
        assert_true(self.node.mailing_updated)

    def test_delete_node_causes_update(self):
        self.node.mailing_enabled = True
        self.node.remove_node(Auth(self.creator))

        self.node.reload()
        assert_true(self.node.mailing_updated)


class TestUpdateListFailure(OsfTestCase):

    @mock.patch('scripts.update_project_mailing_lists.full_update', side_effect=HTTPError(400))
    def test_error_sets_mailing_updated_back_to_true(self, mock_full_update):
        new_node = ProjectFactory()

        update_node(new_node, dry_run=False)
        new_node.reload()

        mock_full_update.assert_called()
        assert_true(new_node.mailing_updated)
