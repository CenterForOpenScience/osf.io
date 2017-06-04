from scripts.fix_embargo_approved_logs import fix_embargo_approved_logs

from website.models import NodeLog

from tests.base import OsfTestCase
from tests.factories import NodeLogFactory, ProjectFactory, RegistrationFactory
from nose.tools import *


class TestFixEmbargoApprovedLogs(OsfTestCase):

    def test_fix_node_param_for_embargo_approved_no_user_log(self):
        project = ProjectFactory()
        registration = RegistrationFactory(project=project)
        embargo_approved_log = NodeLogFactory(action=NodeLog.EMBARGO_APPROVED, params={'node': registration._id})
        fix_embargo_approved_logs([embargo_approved_log])
        embargo_approved_log.reload()
        assert_equal(embargo_approved_log.params['node'], project._id)
        assert_equal(embargo_approved_log.params['registration'], registration._id)
