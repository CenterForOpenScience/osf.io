# -*- coding: utf-8 -*-
import mock
import pytest
from django.utils import timezone

from api.base.settings.defaults import API_BASE
from api.users.views import ClaimUser
from api_tests.utils import only_supports_methods
from framework.auth.core import Auth
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    PreprintFactory,
)

@pytest.mark.django_db
class TestClaimUser:

    @pytest.fixture
    def mock_mail(self):
        with mock.patch('website.project.views.contributor.mails.send_mail') as patch:
            yield patch

    @pytest.fixture()
    def referrer(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, referrer):
        return ProjectFactory(creator=referrer)

    @pytest.fixture()
    def preprint(self, referrer, project):
        return PreprintFactory(creator=referrer, project=project)

    @pytest.fixture()
    def wrong_preprint(self, referrer):
        return PreprintFactory(creator=referrer)

    @pytest.fixture()
    def unreg_user(self, referrer, project):
        return project.add_unregistered_contributor(
            'David Davidson',
            'david@david.son',
            auth=Auth(referrer),
            save=True
        )

    @pytest.fixture()
    def claimer(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url(self):
        return '/{}users/{{}}/claim/'.format(API_BASE)

    def payload(self, **kwargs):
        payload = {
            'data': {
                'attributes': {}
            }
        }
        _id = kwargs.pop('id', None)
        if _id:
            payload['data']['id'] = _id
        if kwargs:
            payload['data']['attributes'] = kwargs
        return payload

    def test_unacceptable_methods(self):
        assert only_supports_methods(ClaimUser, ['POST'])

    def test_claim_unauth_failure(self, app, url, unreg_user, project, wrong_preprint):
        _url = url.format(unreg_user._id)
        # no record locator
        payload = self.payload(email='david@david.son')
        res = app.post_json_api(
            _url,
            payload,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Must specify record "id".'

        # bad record locator
        payload = self.payload(email='david@david.son', id='notaguid')
        res = app.post_json_api(
            _url,
            payload,
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Unable to find specified record.'

        # wrong record locator
        payload = self.payload(email='david@david.son', id=wrong_preprint._id)
        res = app.post_json_api(
            _url,
            payload,
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Unable to find specified record.'

        # no email
        payload = self.payload(id=project._id)
        res = app.post_json_api(
            _url,
            payload,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Must either be logged in or specify claim email.'

        # active user
        _url = url.format(project.creator._id)
        payload = self.payload(email=project.creator.email, id=project._id)
        res = app.post_json_api(
            _url,
            payload,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_claim_unauth_success_with_original_email(self, app, url, project, unreg_user, mock_mail):
        res = app.post_json_api(
            url.format(unreg_user._id),
            self.payload(email='david@david.son', id=project._id),
        )
        assert res.status_code == 204
        assert mock_mail.call_count == 1

    def test_claim_unauth_success_with_claimer_email(self, app, url, unreg_user, project, claimer, mock_mail):
        res = app.post_json_api(
            url.format(unreg_user._id),
            self.payload(email=claimer.username, id=project._id)
        )
        assert res.status_code == 204
        assert mock_mail.call_count == 2

    def test_claim_unauth_success_with_unknown_email(self, app, url, project, unreg_user, mock_mail):
        res = app.post_json_api(
            url.format(unreg_user._id),
            self.payload(email='asdf@fdsa.com', id=project._id),
        )
        assert res.status_code == 204
        assert mock_mail.call_count == 2

    def test_claim_unauth_success_with_preprint_id(self, app, url, preprint, unreg_user, mock_mail):
        res = app.post_json_api(
            url.format(unreg_user._id),
            self.payload(email='david@david.son', id=preprint._id),
        )
        assert res.status_code == 204
        assert mock_mail.call_count == 1

    def test_claim_auth_failure(self, app, url, claimer, wrong_preprint, project, unreg_user, referrer):
        _url = url.format(unreg_user._id)
        # no record locator
        payload = self.payload(email='david@david.son')
        res = app.post_json_api(
            _url,
            payload,
            auth=claimer.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Must specify record "id".'

        # bad record locator
        payload = self.payload(email='david@david.son', id='notaguid')
        res = app.post_json_api(
            _url,
            payload,
            auth=claimer.auth,
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Unable to find specified record.'

        # wrong record locator
        payload = self.payload(email='david@david.son', id=wrong_preprint._id)
        res = app.post_json_api(
            _url,
            payload,
            auth=claimer.auth,
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Unable to find specified record.'

        # referrer auth
        payload = self.payload(email='david@david.son', id=project._id)
        res = app.post_json_api(
            _url,
            payload,
            auth=referrer.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Referrer cannot claim user.'

        # active user
        _url = url.format(project.creator._id)
        payload = self.payload(email=project.creator.email, id=project._id)
        res = app.post_json_api(
            _url,
            payload,
            auth=claimer.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_claim_auth_throttle_error(self, app, url, claimer, unreg_user, project, mock_mail):
        unreg_user.unclaimed_records[project._id]['last_sent'] = timezone.now()
        unreg_user.save()
        res = app.post_json_api(
            url.format(unreg_user._id),
            self.payload(id=project._id),
            auth=claimer.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'User account can only be claimed with an existing user once every 24 hours'
        assert mock_mail.call_count == 0

    def test_claim_auth_success(self, app, url, claimer, unreg_user, project, mock_mail):
        res = app.post_json_api(
            url.format(unreg_user._id),
            self.payload(id=project._id),
            auth=claimer.auth
        )
        assert res.status_code == 204
        assert mock_mail.call_count == 2
