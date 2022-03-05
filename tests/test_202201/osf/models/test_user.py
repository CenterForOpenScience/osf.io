# -*- coding: utf-8 -*-
# Tests ported from tests/test_models.py and tests/test_user.py

import mock
import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from osf.utils import permissions
from osf_tests.factories import UserFactory, ProjectFactory
from framework.auth.exceptions import MergeDisableError

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user():
    return UserFactory()


# Tests copied from tests/test_models.py
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
class TestOSFUser:
    def test_confirm_email_merge_select_for_update(self, user):
        mergee = UserFactory(username='foo@bar.com')
        mergee.temp_account = True
        mergee.save()

        token = user.add_unconfirmed_email('foo@bar.com')

        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            user.confirm_email(token, merge=True)

        mergee.reload()
        assert mergee.is_merged
        assert mergee.merged_by == user

        for_update_sql = connection.ops.for_update_sql()
        assert any(for_update_sql in query['sql'] for query in ctx.captured_queries)

    @mock.patch('osf.utils.requests.settings.SELECT_FOR_UPDATE_ENABLED', False)
    def test_confirm_email_merge_select_for_update_disabled(self, user):
        mergee = UserFactory(username='foo@bar.com')
        mergee.temp_account = True
        mergee.save()

        token = user.add_unconfirmed_email('foo@bar.com')

        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            user.confirm_email(token, merge=True)

        mergee.reload()
        assert mergee.is_merged
        assert mergee.merged_by == user

        for_update_sql = connection.ops.for_update_sql()
        assert not any(for_update_sql in query['sql'] for query in ctx.captured_queries)

    @mock.patch('osf.utils.requests.settings.SELECT_FOR_UPDATE_ENABLED', False)
    def test_confirm_email_save_unregistered_user(self, user):
        mergee = UserFactory(username='foo@bar.com')
        mergee.emails.filter(address='foo@bar.com').delete()
        mergee.temp_account = True
        mergee.save()

        token = user.add_unconfirmed_email('foo@bar.com')

        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            user.confirm_email(token, merge=True)

        mergee.reload()
        assert mergee.is_merged
        assert mergee.merged_by == user
        assert mergee.temp_account == False

    def test_merged_user_with_is_forced_is_false(self, user):
        user2 = UserFactory.build()
        user2.save()

        project = ProjectFactory(is_public=True)
        # Both the master and dupe are contributors
        project.add_contributor(user2, log=False)
        project.add_contributor(user, log=False)
        project.set_permissions(user=user, permissions=permissions.READ)
        project.set_permissions(user=user2, permissions=permissions.ADMIN)
        project.set_visible(user=user, visible=False)
        project.set_visible(user=user2, visible=True)
        project.save()
        with pytest.raises(MergeDisableError) as e:
            user.merge_user(user2, is_forced=False)
        assert str(e.value) == "The merge feature is disabled"
