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
