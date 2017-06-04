from nose.tools import *  # noqa

from tests.base import (
    OsfTestCase,
    fake
)
from tests.factories import (
    UserFactory,
    ProjectFactory
)
from tests import utils

from website.files import models
from tests.test_addons import TestFile
from website.models import MetaSchema
from website.project.model import ensure_schemas
from website.prereg.utils import get_prereg_schema

from scripts.migration.migrate_registration_extra import migrate

class TestMigrateRegistrationExtra(OsfTestCase):
    def setUp(self):
        super(TestMigrateRegistrationExtra, self).setUp()
        self.user = UserFactory()
        self.node = ProjectFactory(creator=self.user)
        ensure_schemas()
        self.prereg_schema = get_prereg_schema()
        self.file = self._get_test_file()
        self.data = {
            'uploader': {
                'extra': {
                    'hasSelectedFile': True,
                    'nodeId': self.node._id,
                    'selectedFileName': 'file.txt',
                    'sha256': fake.sha256(),
                    'viewUrl': '/project/{}/files/osfstorage/5723787136b74e1a953d9612/'.format(
                        self.node._id
                    )
                },
                'value': 'file.txt'
            },
            'other': {
                'value': 'foo'
            },
            'bad': {
                'value': 'foobarbaz',
                'extra': [
                    {
                        'viewUrl': '/project/{}/files/osfstorage/5723787136b74e1a953d9612/'.format(
                            self.node._id
                        ),
                        'hasSelectedFile': True,
                        'selectedFileName': 'file.txt'
                    }
                ]

            },
            'nested': {
                'value': {
                    'uploader': {
                        'extra': {
                            'hasSelectedFile': True,
                            'nodeId': self.node._id,
                            'selectedFileName': 'file.txt',
                            'sha256': fake.sha256(),
                            'viewUrl': '/project/{}/files/osfstorage/5723787136b74e1a953d9612/'.format(
                                self.node._id
                            )
                        },
                        'value': 'file.txt'
                    },
                    'question': {
                        'value': 'bar',
                        'extra': {}
                    },
                    'other': {
                        'value': 'foo',
                        'extra': []

                    }
                }
            }
        }

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

    def test_migrate_registration_extra(self):
        with utils.mock_archive(
                self.node,
                schema=self.prereg_schema,
                data=self.data,
                autocomplete=True,
                autoapprove=True
        ) as reg:
            migrate()
            reg.reload()
            data = reg.registered_meta[self.prereg_schema._id]
            assert_true(
                isinstance(data['uploader']['extra'], list)
            )
            assert_true(
                isinstance(
                    data['nested']['value']['uploader']['extra'],
                    list
                )
            )
            assert_true(
                isinstance(
                    data['nested']['value']['question']['extra'],
                    list
                )
            )
            assert_equal(
                self.data['uploader']['extra'],
                data['uploader']['extra'][0]
            )
            assert_equal(
                self.data['nested']['value']['uploader']['extra'],
                data['nested']['value']['uploader']['extra'][0]
            )
            assert_equal(
                self.data['nested']['value']['question']['value'],
                data['nested']['value']['question']['value']
            )
            assert_equal(
                self.data['nested']['value']['other'],
                data['nested']['value']['other']
            )
            assert_equal(
                self.data['other'],
                data['other']
            )
            assert_true(
                data['bad']['extra'][0].get('data', False)
            )
            assert_true(
                isinstance(data['bad']['extra'][0]['data'], dict)
            )
            assert_equal(
                data['bad']['extra'][0]['data']['name'], 'file.txt'
            )
            assert_equal(
                data['bad']['extra'][0]['data']['sha256'], '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892'
            )
