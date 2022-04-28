# -*- coding: utf-8 -*-
# Tests ported from tests/test_models.py and tests/test_user.py
from __future__ import absolute_import

import mock
import pytest
from nose.tools import assert_equal
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from osf.models import OSFUser
from tests.base import OsfTestCase
from osf.utils import permissions
from osf_tests.factories import AuthUserFactory, InstitutionFactory, UserFactory, ProjectFactory
from framework.auth.exceptions import MergeDisableError

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user():
    return UserFactory()


# Tests copied from tests/test_models.py
@pytest.mark.enable_implicit_clean
@pytest.mark.enable_quickfiles_creation
@pytest.mark.skip('Clone test case from osf/models/user.py '
                  'for making coverage')
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

        with transaction.atomic(), CaptureQueriesContext(connection):
            user.confirm_email(token, merge=True)

        mergee.reload()
        assert mergee.is_merged
        assert mergee.merged_by == user
        assert mergee.temp_account is False

    @mock.patch('website.settings.ENABLE_USER_MERGE', False)
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
        assert str(e.value) == 'The merge feature is disabled'


class TestPropertyIsFullAccountRequiredInfo(OsfTestCase):

    def setUp(self):
        super(TestPropertyIsFullAccountRequiredInfo, self).setUp()

    def test_is_full_account_required_info_miss_institution(self):
        user_auth = AuthUserFactory()
        assert_equal(user_auth.is_full_account_required_info, True)

    def test_is_full_account_required_info_miss_jobs(self):
        user_auth = AuthUserFactory()
        institution = InstitutionFactory()
        user_auth.affiliated_institutions.add(institution)
        assert_equal(user_auth.is_full_account_required_info, False)

    def test_is_full_account_required_info_has_jobs(self):
        name = 'name'
        user_auth = AuthUserFactory(fullname=name)
        institution = InstitutionFactory()
        user_auth.affiliated_institutions.add(institution)
        user_auth.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'title': 'Lover Boy',
            'startMonth': 1,
            'startYear': '1970',
            'endMonth': 1,
            'endYear': '1980',
            'institution_ja': 'Organization JP'
        }]

        user_auth.save()
        user = OSFUser.objects.filter(fullname=name).first()
        assert user
        assert user.jobs
        assert_equal(user_auth.is_full_account_required_info, False)

    @mock.patch('osf.models.user.OSFUser.ext', new_callable=mock.PropertyMock)
    def test_is_full_account_required_info_exception(self, mock_idp_attr):
        family_name_en = 'family name en'
        family_name_ja = 'family name ja'
        given_name_en = 'given_name en'
        given_name_ja = 'given_name ja'
        user_auth = AuthUserFactory()
        user_auth.family_name = family_name_en
        user_auth.family_name_ja = family_name_ja
        user_auth.given_name = given_name_en
        user_auth.given_name_ja = given_name_ja
        institution = InstitutionFactory()
        user_auth.affiliated_institutions.add(institution)
        user_auth.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'title': 'Lover Boy',
            'startMonth': 1,
            'startYear': '1970',
            'endMonth': 1,
            'endYear': '1980',
            'institution_ja': 'Organization JP'
        }]
        user_auth.save()
        mock_idp_attr.side_effect = AttributeError('exception')
        assert_equal(user_auth.is_full_account_required_info, True)
