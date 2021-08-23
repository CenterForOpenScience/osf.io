# -*- coding: utf-8 -*-

import pytest
import datetime

from osf_tests.factories import (
    AuthUserFactory,
    DraftRegistrationFactory
)

from scripts.remove_after_use.fix_draft_node_permissions import main as fix_permissions

from website import settings
from tests.json_api_test_app import JSONAPITestApp

from osf.models.contributor import get_contributor_permission, DraftRegistrationContributor

@pytest.fixture()
def app():
    return JSONAPITestApp()


@pytest.mark.django_db
class TestFixDraftNodePermissions:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def bugged_reg(self, user, write_contrib):
        draft_registration = DraftRegistrationFactory(creator=user)
        draft_registration.branched_from.add_contributor(write_contrib, permissions='write', visible=True)
        draft_registration.contributor_set.all().delete()
        draft_registration.created = datetime.datetime(2017, 2, 4, 0, 0)  # A date before the migration
        for group in draft_registration.group_objects:
            group.user_set.clear()

        draft_registration.save()
        return draft_registration

    @pytest.fixture()
    def url(self, bugged_reg):
        return f'{settings.API_DOMAIN}v2/draft_registrations/{bugged_reg._id}/relationships/subjects/'

    def test_fix_draft_node_permissions(self, app, bugged_reg, user, write_contrib, url):
        assert not bugged_reg.contributors

        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

        fix_permissions(dry=False)
        assert bugged_reg.contributors.count() == 2
        assert user in bugged_reg.contributors
        assert write_contrib in bugged_reg.contributors

        admin_contrib = DraftRegistrationContributor.objects.get(user=user)
        assert get_contributor_permission(admin_contrib, bugged_reg) == 'admin'

        write_contrib = DraftRegistrationContributor.objects.get(user=write_contrib)
        assert get_contributor_permission(write_contrib, bugged_reg) == 'write'
        assert write_contrib.visible

        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        # Make sure we didn't just leave open the barn door.
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
