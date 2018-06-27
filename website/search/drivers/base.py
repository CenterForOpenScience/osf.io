import abc
from osf import models


class SearchDriver(object):

    __metaclass__ = abc.ABCMeta

    # TODO Remove me
    DOC_TYPE_TO_MODEL = {
        'component': models.AbstractNode,
        'file': models.BaseFileNode,
        'institution': models.Institution,
        'preprint': models.AbstractNode,
        'project': models.AbstractNode,
        'registration': models.AbstractNode,
        'user': models.OSFUser,
    }

    @abc.abstractproperty
    def migrator(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def search(self, query, index=None, doc_type=None, raw=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def search_contributor(query, page=0, size=10, exclude=None, current_user=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def update_node(self, node, index=None, bulk=False, async=True, saved_fields=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def bulk_update_nodes(self, serialize, nodes, index=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def update_contributors_async(self, user_id):
        raise NotImplementedError()

    @abc.abstractmethod
    def update_user(self, user, index=None, async=True):
        raise NotImplementedError()

    @abc.abstractmethod
    def update_file(self, file_, index=None, delete=False):
        raise NotImplementedError()

    @abc.abstractmethod
    def update_collected_metadata(self, file_, index=None, delete=False):
        raise NotImplementedError()

    @abc.abstractmethod
    def bulk_update_collected_metadata(self, file_, index=None, delete=False):
        raise NotImplementedError()

    @abc.abstractmethod
    def update_institution(self, institution, index=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def delete_all(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def delete_index(self, index):
        raise NotImplementedError()

    @abc.abstractmethod
    def delete_node(self, node, index=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def create_index(self, index=None):
        raise NotImplementedError()


class SearchMigrator(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, driver):
        self._driver = driver

    def _before_migrate(self):
        pass

    def _after_migrate(self):
        pass

    def migrate(self, types=None):
        types = types or ('users', 'files', 'institutions', 'collections', 'projects', 'registrations', 'preprints', 'components', 'collection-submissions')

        self.setup()
        self._before_migrate()

        if 'institutions' in types:
            self.migrate_institutions()

        if 'projects' in types:
            self.migrate_projects()

        if 'registrations' in types:
            self.migrate_registrations()

        if 'components' in types:
            self.migrate_components()

        if 'preprints' in types:
            self.migrate_preprints()

        if 'files' in types:
            self.migrate_files()

        if 'users' in types:
            self.migrate_users()

        if 'collection-submissions' in types:
            self.migrate_collection_submissions()

        self._after_migrate()

    @abc.abstractmethod
    def setup(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def teardown(self):
        raise NotImplementedError()

    # @abc.abstractmethod
    # def migrate_nodes(self):
    #     raise NotImplementedError()

    @abc.abstractmethod
    def migrate_files(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def migrate_users(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def migrate_institutions(self):
        raise NotImplementedError()
