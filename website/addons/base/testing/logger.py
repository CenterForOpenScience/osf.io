from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth

from tests.factories import ProjectFactory
from website.project.model import NodeLog

# TODO
class TestNodeLogger(object):

    def test_log_file_added(self):
        logger = None
        logger.log(NodeLog.FILE_ADDED, save=True)

        last_log = self.project.logs[-1]

        assert_equal(last_log.action, "box_{0}".format(NodeLog.FILE_ADDED))

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/1557
    def test_log_deauthorized_when_node_settings_are_deleted(self):
        project = ProjectFactory()
        project.add_addon('box', auth=Auth(project.creator))
        dbox_settings = project.get_addon('box')
        dbox_settings.delete(save=True)
        # sanity check
        assert_true(dbox_settings.deleted)

        logger = utils.BoxNodeLogger(node=project, auth=Auth(self.user))
        logger.log(action='node_deauthorized', save=True)

        last_log = project.logs[-1]
        assert_equal(last_log.action, 'box_node_deauthorized')
