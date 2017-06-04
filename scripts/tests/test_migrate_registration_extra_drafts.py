from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import UserFactory
from tests.factories import DraftRegistrationFactory, ProjectFactory

from website.files import models
from tests.test_addons import TestFile
from website.models import MetaSchema
from website.project.model import ensure_schemas
from website.prereg.utils import get_prereg_schema
from scripts.migration.migrate_registration_extra_drafts import main



class TestMigrateRegistrationExtra(OsfTestCase):
    def _get_test_file(self):
        version = models.FileVersion(identifier='1', provider='osfstorage', metadata={'sha256': '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892'})
        version.save()
        ret = models.FileNode(
            _id='5723787136b74e1a953d9612',
            name='file.txt',
            node=self.node,
            provider='osfstorage',
            path='/test/file.txt',
            materialized_path='/test/file.txt',
            versions=[version]
        )
        ret.save()
        return ret

    def setUp(self):
        super(TestMigrateRegistrationExtra, self).setUp()
        self.user = UserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.file = self._get_test_file()
        MetaSchema.remove()
        ensure_schemas()


        self.file_ans = {
            'file': {
                'data':{
                    'kind':'file',
                    'extra':{
                        'checkout': None,
                        'hashes':{
                            'sha256':'1fffe6116ecfa778f9938060d5caab923ba4b8db60bd2dd57f16a72e5ef06292'
                        },
                        'downloads':0,
                        'version':1
                    },
                    'modified':'2016-04-15T18:10:48',
                    'name':'file.txt',
                    'provider':'osfstorage',
                }
            }
        }
        self.complex_metadata = {
            'q1': {
                'value': 'Answer 1',
                'extra': []
            },
            'q2': {
                'value': 'Answer 2',
                'extra': {}
            },
            'q3': {
                'value': 'Answer 3',
                'extra': self.file_ans
            },
            'q4': {
                'value': {
                    'question': {
                        'value': 'Answer 4',
                        'extra': {}
                    },
                    'uploader': {
                        'value': '',
                        'extra': {}
                    }
                },
            },
            'q5': {
                'value': 'Answer 5',
                'extra': [
                    {
                        'viewUrl': '/project/abcdef/files/osfstorage/5723787136b74e1a953d9612/',
                        'hasSelectedFile': True,
                        'selectedFileName': 'file.txt'
                    }
                ]
            }
        }
        self.simple_metadata = {
            'Summary': 'Some airy'
        }
        self.schema = get_prereg_schema()
        self.draft1 = DraftRegistrationFactory(
            registration_metadata=self.complex_metadata,
            registration_schema=self.schema,
            approval=None,
            registered_node=None

        )
        self.draft2 = DraftRegistrationFactory(
            registration_metadata=self.simple_metadata
        )

    def test_migrate_registration_extra(self):

        assert_equal(type(self.draft1.registration_metadata['q1']['extra']), list)
        assert_equal(type(self.draft1.registration_metadata['q2']['extra']), dict)
        assert_equal(type(self.draft1.registration_metadata['q2']['extra']), dict)
        assert_equal(type(self.draft1.registration_metadata['q4']['value']['question']['extra']), dict)

        assert_equal(self.draft2.registration_metadata, self.simple_metadata)

        main(dry=False)
        self.draft1.reload()
        self.draft2.reload()

        assert_equal(type(self.draft1.registration_metadata['q1']['extra']), list)
        assert_equal(type(self.draft1.registration_metadata['q2']['extra']), list)
        assert_equal(type(self.draft1.registration_metadata['q3']['extra']), list)

        assert_equal(self.draft1.registration_metadata['q3']['extra'][0], self.file_ans)

        assert_equal(type(self.draft1.registration_metadata['q4']['value']['question']['extra']), list)

        assert_true(self.draft1.registration_metadata['q5']['extra'][0].get('data', False))
        assert_equal(type(self.draft1.registration_metadata['q5']['extra'][0]['data']), dict)
        assert_equal(self.draft1.registration_metadata['q5']['extra'][0]['data']['name'], 'file.txt')
        assert_equal(self.draft1.registration_metadata['q5']['extra'][0]['data']['sha256'], '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892')

        assert_equal(self.draft2.registration_metadata, self.simple_metadata)
