from nose.tools import *  # flake8: noqa

from website.util import permissions

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)


class ViewOnlyLinkTestCase(ApiTestCase):

    def setUp(self):
        super(ViewOnlyLinkTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.read_only_user = AuthUserFactory()
        self.read_write_user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_contributor(self.read_only_user, permissions=[permissions.READ])
        self.public_project.add_contributor(self.read_write_user, permissions=[permissions.WRITE])
        self.public_project.save()


class TestViewOnlyLinksList(ViewOnlyLinkTestCase):

    def test_admin_can_view_vols_list(self):
        pass

    def test_read_write_cannot_view_vols_list(self):
        pass

    def test_read_only_cannot_view_vols_list(self):
        pass

    def test_logged_in_user_cannot_view_vols_list(self):
        pass

    def test_unauthenticated_user_cannot_view_vols_list(self):
        pass

    def test_deleted_vols_not_returned(self):
        pass
