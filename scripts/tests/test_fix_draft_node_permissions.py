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


@pytest.fixture()
def app():
    return JSONAPITestApp()


@pytest.mark.django_db
class TestFixDraftNodePermissions:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def bugged_reg(self, user):
        draft_registration = DraftRegistrationFactory(creator=user)
        draft_registration.created = datetime.datetime(2017, 2, 4, 0, 0)  # A date before the migration
        for group in draft_registration.group_objects:
            group.user_set.clear()

        draft_registration.save()
        return draft_registration

    @pytest.fixture()
    def url(self, bugged_reg):
        return f'{settings.API_DOMAIN}v2/draft_registrations/{bugged_reg._id}/relationships/subjects/'

    def test_fix_draft_node_permissions(self, app, bugged_reg, user, url):

        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

        fix_permissions(dry=False)

        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        # Make sure we didn't just leave open the barn door.
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
