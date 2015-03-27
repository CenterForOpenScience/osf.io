import copy
import logging

from modularodm import Q, fields
from modularodm.exceptions import NoResultsFound

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.addons.osfstorage import model, oldels

logger = logging.getLogger(__name__)


def migrate_download_counts(node, old, new, dry=True):
    collection = database['pagecounters']

    new_id = ':'.join(['download', node._id, new._id])
    old_id = ':'.join(['download', node._id, old.path])

    for doc in collection.find({'_id': {'$regex': '^{}(:\d)?'.format(old_id)}}):
        new_doc = copy.deep(doc)
        doc['_id'] = doc['_id'].replace(old_id, new_id)
        collection.update(doc, new_doc)


def migrate_node_settings(node_settings, dry=True):
    logger.info('Running `on add` for node settings of {}'.format(node_settings.owner._id))

    if not dry:
        node_settings.on_add()

def migrate_file(node, old, parent, dry=True):
    assert isinstance(old, oldels.OsfStorageFileRecord)
    logger.info('Creating new child {}'.format(old.name))
    if not dry:
        new = parent.append_file(old.name)
        new.versions = old.versions
        new.is_deleted = old.is_deleted
    else:
        new = None

    migrate_guid(node, old, new, dry=dry)
    migrate_download_counts(node, old, new, dry=dry)


def migrate_guid(node, old, new, dry=True):
    try:
        guid = model.OsfStorageGuidFile.find_one(
            Q('node', 'eq', node) &
            Q('path', 'eq', old.path)
        )
        logger.info('Migrating file guid {}'.format(guid._id))
    except NoResultsFound:
        logger.info('No guids found for {}'.format(new.path))
        return

    if not dry:
        guid.path = new.path
        guid.save()

def migrate_children(node_settings, dry=True):
    logger.info('Migrating children of node {}', node_settings.owner._id)
    for child in node_settings.file_tree.children:
        migrate_file(node_settings.owner, child, node_settings.root_node, dry=dry)


def main(dry=True):
    for node_settings in model.OsfStorageNodeSettings.find():
        try:
            with TokuTransaction():
                migrate_node_settings(node_settings.owner, node_settings, dry=dry)
                migrate_children(node_settings, dry=dry)
        except Exception as error:
            logger.error('Could no migrate file tree from {}'.format(node_settings.owner._id))
            logger.exception(error)


if __name__ == '__main__':
    import sys
    dry = 'dry' in sys.argv
    init_app(set_backends=True, routes=False)
    main(dry=dry)


from framework.auth import Auth
from tests.base import OsfTestCase
from tests.factories import ProjectFactory

class TestMigrateOldels(OsfTestCase):

    def setUp(self):
        super(TestMigrateOldels, self).setUp()
        # Hack to avoid calling on add
        self.osf_storage_on_add = model.OsfStorageNodeSettings.on_add
        model.OsfStorageNodeSettings.on_add = lambda *_, **__: None

        self.project = ProjectFactory()
        self.user = self.project.creator
        self.auth = Auth(user=self.user)

        self.project.add_addon('osfstorage', None)
        self.node_settings = self.project.get_addon('osfstorage')
        tree, _ = oldels.OsfStorageFileTree.get_or_create('', self.node_settings)
        tree.save()
        self.node_settings.file_tree = tree
        self.node_settings.save()
        model.OsfStorageNodeSettings.on_add = self.osf_storage_on_add

    def test_creates_root_node(self):
        assert self.node_settings.root_node is None
        migrate_node_settings(self.node_settings, dry=False)
        assert self.node_settings.root_node is not None
        assert not self.node_settings._dirty

    def test_migrates_files(self):
        names = []
        for num in range(10):
            names.append('DEAR GOD! {} CARPNADOS'.format(num))
            oldels.OsfStorageFileRecord.get_or_create(names[-1], self.node_settings)

        assert len(self.node_settings.file_tree.children) == 10

        migrate_node_settings(self.node_settings, dry=False)
        migrate_children(self.node_settings, dry=False)

        children = self.node_settings.root_node.children

        assert not self.node_settings._dirty
        assert self.node_settings.root_node is not None
        assert not self.node_settings.root_node._dirty

        assert len(children) == 10

        for child in children:
            names.remove(child.name)

        assert len(names) == 0

    def test_migrates_guids(self):
        names = []
        for num in range(10):
            names.append('DEAR GOD! {} CARPNADOS'.format(num))
            guid = model.OsfStorageGuidFile(node=self.project, path=names[-1])
            guid.save()
            oldels.OsfStorageFileRecord.get_or_create(names[-1], self.node_settings)

        assert len(model.OsfStorageGuidFile.find()) == 10

        migrate_node_settings(self.node_settings, dry=False)
        migrate_children(self.node_settings, dry=False)

        guids = model.OsfStorageGuidFile.find()
        paths = [x.path for x in model.OsfStorageFileNode.find(Q('kind', 'eq', 'file') & Q('node_settings', 'eq', self.node_settings))]
        assert len(guids) == 10
        for guid in guids:
            paths.remove(guid.path)
        assert len(paths) == 0
