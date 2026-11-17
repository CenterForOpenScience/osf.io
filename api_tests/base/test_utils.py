from unittest import mock
import unittest
import pytest
from importlib import import_module
from django.conf import settings as django_conf_settings

from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from rest_framework import fields

from api.base import utils as api_utils
from osf.models import AbstractNode
from osf.models.base import coerce_guid, Guid, GuidMixin, OptionalGuidMixin, VersionedGuidMixin, InvalidGuid
from osf_tests.factories import ProjectFactory, PreprintFactory
from tests.test_websitefiles import TestFile
from framework.status import push_status_message

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


class TestTruthyFalsy:
    """Check that our copy/pasted representation of
    TRUTHY and FALSY match the DRF BooleanField's versions
    """

    def test_truthy(self):
        assert api_utils.TRUTHY == fields.BooleanField.TRUE_VALUES

    def test_falsy(self):
        assert api_utils.FALSY == fields.BooleanField.FALSE_VALUES


class TestIsDeprecated(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.min_version = '2.0'
        self.max_version = '2.5'

    def test_is_deprecated(self):
        request_version = '2.6'
        is_deprecated = api_utils.is_deprecated(request_version, self.min_version, self.max_version)
        assert is_deprecated is True

    def test_is_not_deprecated(self):
        request_version = '2.5'
        is_deprecated = api_utils.is_deprecated(request_version, self.min_version, self.max_version)
        assert is_deprecated is False

    def test_is_deprecated_larger_versions(self):
        request_version = '2.10'
        is_deprecated = api_utils.is_deprecated(request_version, self.min_version, self.max_version)
        assert is_deprecated is True


@pytest.mark.django_db
@mock.patch('osf.utils.requests.settings.SELECT_FOR_UPDATE_ENABLED', True)
class TestGetObjectOrErrorSelectForUpdate:

    @pytest.fixture()
    def node(self):
        return ProjectFactory()

    @staticmethod
    def lock_queries(ctx):
        for_update_sql = connection.ops.for_update_sql()
        return [query for query in ctx.captured_queries if for_update_sql in query['sql']]

    def test_locks_row_on_mutating_request_by_default(self, node):
        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            obj = api_utils.get_object_or_error(AbstractNode, node._id, mock.Mock(method='POST'))

        assert obj == node
        assert self.lock_queries(ctx)

    def test_does_not_lock_row_when_select_for_update_not_allowed(self, node):
        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            obj = api_utils.get_object_or_error(
                AbstractNode,
                node._id,
                mock.Mock(method='POST'),
                allow_select_for_update=False,
            )

        assert obj == node
        assert not self.lock_queries(ctx)

    def test_does_not_lock_row_on_safe_request(self, node):
        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            obj = api_utils.get_object_or_error(AbstractNode, node._id, mock.Mock(method='GET'))

        assert obj == node
        assert not self.lock_queries(ctx)

@pytest.mark.django_db
class TestFlaskDjangoIntegration:
    def test_push_status_message_no_response(self):
        status_message = 'This is a message'
        statuses = ['info', 'warning', 'warn', 'success', 'danger', 'default']
        for status in statuses:
            try:
                with mock.patch('framework.status.get_session', return_value=SessionStore()):
                    push_status_message(status_message, kind=status)
            except BaseException:
                assert False, f'Exception from push_status_message via API v2 with type "{status}".'


@pytest.mark.django_db
class TestCoerceGuid:

    def test_guid_instance(self):
        project = ProjectFactory()
        assert isinstance(project.guids.first(), Guid)
        assert coerce_guid(project.guids.first()) == project.guids.first()

    def test_versioned_guid_instance(self):
        preprint = PreprintFactory()
        assert isinstance(preprint, VersionedGuidMixin)
        assert coerce_guid(preprint) == preprint.versioned_guids.first().guid

    def test_guid_mixin_instance(self):
        project = ProjectFactory()
        assert isinstance(project, GuidMixin)
        assert coerce_guid(project._id) == project.guids.first()

    def test_str_guid_instance(self):
        project = ProjectFactory()
        str_guid = str(project._id)
        guid = coerce_guid(str_guid)
        assert isinstance(guid, Guid)
        assert guid == project.guids.first()

    def test_incorrect_str_guid_instance(self):
        incorrect_guid = '12345'
        with pytest.raises(InvalidGuid, match='guid does not exist'):
            assert coerce_guid(incorrect_guid)

    def test_optional_guid_instance(self):
        node = ProjectFactory()
        test_file = TestFile(
            _path='anid',
            name='name',
            target=node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        test_file.save()
        test_file.get_guid(create=True)
        assert isinstance(test_file, OptionalGuidMixin)
        assert coerce_guid(test_file) == test_file.guids.first()

    def test_incorrect_optional_guid_instance(self):
        node = ProjectFactory()
        test_file = TestFile(
            _path='anid',
            name='name',
            target=node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        test_file.save()
        assert isinstance(test_file, OptionalGuidMixin)
        with pytest.raises(InvalidGuid, match='guid does not exist'):
            assert coerce_guid(test_file)

    def test_invalid_guid(self):
        incorrect_guid = 12345
        with pytest.raises(InvalidGuid, match='cannot coerce'):
            assert coerce_guid(incorrect_guid)
