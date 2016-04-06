from nose import tools as nt

from tests.base import AdminTestCase

from admin.common_auth.logs import OSFLogEntry, update_admin_log


class TestUpdateAdminLog(AdminTestCase):
    def test_add_log(self):
        update_admin_log('123', 'dfqc2', 'This', 'log_added')
        nt.assert_equal(OSFLogEntry.objects.count(), 1)
        log = OSFLogEntry.objects.latest('action_time')
        nt.assert_equal(log.user_id, 123)
