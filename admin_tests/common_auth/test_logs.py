from nose import tools as nt

from tests.base import AdminTestCase

from osf.models.admin_log_entry import AdminLogEntry, update_admin_log


class TestUpdateAdminLog(AdminTestCase):
    def test_add_log(self):
        update_admin_log('123', 'dfqc2', 'This', 'log_added')
        nt.assert_equal(AdminLogEntry.objects.count(), 1)
        log = AdminLogEntry.objects.latest('action_time')
        nt.assert_equal(log.user_id, 123)
