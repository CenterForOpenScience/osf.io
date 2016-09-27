from modularodm import Q

from website.files.models import StoredFileNode
from website.files.models.dropbox import DropboxFile
from website.files.models.github import GithubFile
from website.files.models.googledrive import GoogleDriveFile
from website.files.models.s3 import S3File
from scripts.fix_materialized_paths import update_file_materialized_paths

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from nose.tools import *  # noqa PEP8 asserts


class FixMaterializedPathTestMixin(object):
    @property
    def provider(self):
        raise NotImplementedError

    @property
    def ProviderFile(self):
        raise NotImplementedError

    def setUp(self):
        super(FixMaterializedPathTestMixin, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

    def test_exclude_correct_file_materialized_path(self):
        test_file = self.ProviderFile.create(
            is_file=True,
            node=self.project,
            path='/test',
            name='test',
            materialized_path='/test',
        )
        test_file.save()
        targets = StoredFileNode.find(Q('provider', 'ne', 'osfstorage'))
        assert_not_in(test_file, targets)

    def test_fix_incorrect_file_materialized_path(self):
        test_file = self.ProviderFile.create(
            is_file=True,
            node=self.project,
            path='/path',
            name='path',
            materialized_path='path',
        )
        test_file.save()
        targets = StoredFileNode.find(Q('provider', 'ne', 'osfstorage'))
        update_file_materialized_paths(targets)
        test_file.reload()
        assert_equal(test_file.materialized_path, '/path')

    def tearDown(self):
        super(FixMaterializedPathTestMixin, self).tearDown()
        StoredFileNode.remove()


class TestFixDropboxMaterializedPaths(FixMaterializedPathTestMixin, OsfTestCase):

    provider = 'dropbox'
    ProviderFile = DropboxFile


class TestFixGoogleDriveMaterializedPaths(FixMaterializedPathTestMixin, OsfTestCase):

    provider = 'googledrive'
    ProviderFile = GoogleDriveFile


class TestFixGithubMaterializedPaths(FixMaterializedPathTestMixin, OsfTestCase):

    provider = 'github'
    ProviderFile = GithubFile


class TestFixS3MaterializedPaths(FixMaterializedPathTestMixin, OsfTestCase):

    provider = 's3'
    ProviderFile = S3File
