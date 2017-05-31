# -*- coding: utf-8 -*-
import mock
import pytest

from django.db import DataError
from django.utils import timezone

from framework.auth import cas
from osf.exceptions import ValidationError
from osf_tests.factories import ApiOAuth2ApplicationFactory
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db


class TestApiOAuth2Application(OsfTestCase):
    def setUp(self):
        super(TestApiOAuth2Application, self).setUp()
        self.api_app = ApiOAuth2ApplicationFactory()

    @pytest.mark.skip('Owner should not be nullable after migration')
    def test_must_have_owner(self):
        with pytest.raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(owner=None)
            api_app.save()

    def test_client_id_auto_populates(self):
        assert len(self.api_app.client_id) > 0

    def test_client_secret_auto_populates(self):
        assert len(self.api_app.client_secret) > 0

    def test_new_app_is_not_flagged_as_deleted(self):
        assert self.api_app.is_active is True

    # https://docs.djangoproject.com/en/1.9/ref/models/fields/#editable
    @pytest.mark.skip('Django\'s editable=False does not prevent edits')
    def test_cant_edit_creation_date(self):
        with pytest.raises(AttributeError):
            self.api_app.date_created = timezone.now()

    def test_invalid_home_url_raises_exception(self):
        with pytest.raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(home_url="Totally not a URL")
            api_app.save()

    def test_invalid_callback_url_raises_exception(self):
        with pytest.raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(callback_url="itms://itunes.apple.com/us/app/apple-store/id375380948?mt=8")
            api_app.save()

    def test_name_cannot_be_blank(self):
        with pytest.raises(ValidationError):
            api_app = ApiOAuth2ApplicationFactory(name='')
            api_app.save()

    def test_long_name_raises_exception(self):
        long_name = ('JohnJacobJingelheimerSchmidtHisNameIsMyN' * 5) + 'a'
        with pytest.raises(DataError):
            api_app = ApiOAuth2ApplicationFactory(name=long_name)
            api_app.save()

    def test_long_description_raises_exception(self):
        long_desc = ('JohnJacobJingelheimerSchmidtHisNameIsMyN' * 25) + 'a'
        with pytest.raises(DataError):
            api_app = ApiOAuth2ApplicationFactory(description=long_desc)
            api_app.save()

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_active_set_to_false_upon_successful_deletion(self, mock_method):
        mock_method.return_value(True)
        self.api_app.deactivate(save=True)
        self.api_app.reload()
        assert self.api_app.is_active is False

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_active_remains_true_when_cas_token_deletion_fails(self, mock_method):
        mock_method.side_effect = cas.CasHTTPError("CAS can't revoke tokens", 400, 'blank', 'blank')
        with pytest.raises(cas.CasHTTPError):
            self.api_app.deactivate(save=True)
        self.api_app.reload()
        assert self.api_app.is_active is True

