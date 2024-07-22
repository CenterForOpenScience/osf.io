import abc

from framework.auth import Auth
from osf_tests.factories import AuthUserFactory, ProjectFactory

class AddonNodeLoggerTestSuiteMixinBase:

    __metaclass__ = abc.ABCMeta

    @property
    @abc.abstractmethod
    def addon_short_name(self):
        pass

    @property
    @abc.abstractmethod
    def NodeLogger(self):
        pass

    def setUp(self):
        super().setUp()
        self.auth = Auth(AuthUserFactory())
        self.node = ProjectFactory(creator=self.auth.user)
        self.path = None
        self.node.add_addon(self.addon_short_name, auth=self.auth)
        self.logger = self.NodeLogger(node=self.node, auth=self.auth)


class StorageAddonNodeLoggerTestSuiteMixin(AddonNodeLoggerTestSuiteMixinBase):

    def setUp(self):
        super().setUp()

    def test_log_file_added(self):
        self.logger.log('file_added', save=True)
        last_log = self.node.logs.latest()

        assert last_log.action == '{}_{}'.format(self.addon_short_name, 'file_added')

    def test_log_file_removed(self):
        self.logger.log('file_removed', save=True)
        last_log = self.node.logs.latest()

        assert last_log.action == '{}_{}'.format(self.addon_short_name, 'file_removed')

    def test_log_deauthorized_when_node_settings_are_deleted(self):
        node_settings = self.node.get_addon(self.addon_short_name)
        node_settings.delete(save=True)
        # sanity check
        assert node_settings.deleted

        self.logger.log(action='node_deauthorized', save=True)

        last_log = self.node.logs.latest()
        assert last_log.action == f'{self.addon_short_name}_node_deauthorized'
