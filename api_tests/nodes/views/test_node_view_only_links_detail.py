from nose.tools import *  # flake8: noqa

from test_node_view_only_links_list import ViewOnlyLinkTestCase

from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)


class TestViewOnlyLinksDetail(ViewOnlyLinkTestCase):

    def test_admin_can_view_vol_detail(self):
        pass

    def test_read_write_cannot_view_vol_detail(self):
        pass

    def test_read_only_cannot_view_vol_detail(self):
        pass

    def test_logged_in_user_cannot_view_vol_detail(self):
        pass

    def test_unauthenticated_user_cannot_view_vol_detail(self):
        pass

    def test_deleted_vols_not_returned(self):
        pass


class TestViewOnlyLinksCreate(ViewOnlyLinkTestCase):

    def test_id_reqired_in_payload(self):
        pass

    def test_invalid_vol_id(self):
        pass

    def test_invalid_vol_name(self):
        pass

    def test_nodes_required_in_payload(self):
        pass

    def test_invalid_nodes_in_payload(self):
        pass

    def test_admin_can_create_vol(self):
        pass

    def test_read_write_cannot_create_vol(self):
        pass

    def test_read_only_cannot_create_vol(self):
        pass

    def test_logged_in_user_cannot_create_vol(self):
        pass

    def test_unauthenticated_user_cannot_create_vol(self):
        pass


class TestViewOnlyLinksUpdate(ViewOnlyLinkTestCase):

    def test_id_reqired_in_payload(self):
        pass

    def test_invalid_vol_id(self):
        pass

    def test_invalid_vol_name(self):
        pass

    def test_nodes_required_in_payload(self):
        pass

    def test_invalid_nodes_in_payload(self):
        pass

    def test_admin_can_update_vol(self):
        pass

    def test_read_write_cannot_update_vol(self):
        pass

    def test_read_only_cannot_update_vol(self):
        pass

    def test_logged_in_user_cannot_update_vol(self):
        pass

    def test_unauthenticated_user_cannot_update_vol(self):
        pass


class TestViewOnlyLinksDelete(ViewOnlyLinkTestCase):

    def test_id_reqired_in_payload(self):
        pass

    def test_invalid_vol_id(self):
        pass

    def test_nodes_required_in_payload(self):
        pass

    def test_invalid_nodes_in_payload(self):
        pass

    def test_admin_can_delete_vol(self):
        pass

    def test_read_write_cannot_delete_vol(self):
        pass

    def test_read_only_cannot_delete_vol(self):
        pass

    def test_logged_in_user_cannot_delete_vol(self):
        pass

    def test_unauthenticated_user_cannot_delete_vol(self):
        pass
