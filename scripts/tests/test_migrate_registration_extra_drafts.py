from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import UserFactory
from tests.factories import DraftRegistrationFactory

from website.models import MetaSchema
from website.project.model import ensure_schemas
from website.prereg.utils import get_prereg_schema
from scripts.migration.migrate_registration_extra_drafts import main



class TestMigrateRegistrationExtra(OsfTestCase):
    def setUp(self):
        super(TestMigrateRegistrationExtra, self).setUp()
        self.user = UserFactory()
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

        assert_equal(self.draft2.registration_metadata, self.simple_metadata)
