from api.base.settings.defaults import API_BASE
from api.preprints.permissions import MIGRATED_PREPRINT_ERROR
from osf.utils import permissions
from osf.utils.workflows import DefaultStates, RequestTypes
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    PreprintFactory,
    PreprintRequestFactory,
    ProjectFactory,
    SubjectFactory,
)
from tests.base import ApiTestCase


class TestMigratedPreprint(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.admin = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.admin)
        self.preprint.add_contributor(self.write_contrib, permissions=permissions.WRITE)
        self.preprint.is_migrated = True
        self.preprint.save()

        self.url = f'/{API_BASE}preprints/{self.preprint._id}/'
        self.contributors_url = f'{self.url}contributors/'
        self.write_contrib_url = f'{self.contributors_url}{self.write_contrib._id}/'

    def update_payload(self, preprint, **attributes):
        return {
            'data': {
                'id': preprint._id,
                'type': 'preprints',
                'attributes': attributes,
            }
        }

    def update_contributor_payload(self, **attributes):
        return {
            'data': {
                'id': f'{self.preprint._id}-{self.write_contrib._id}',
                'type': 'contributors',
                'attributes': attributes,
            }
        }

    def assert_rejected(self, res):
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == MIGRATED_PREPRINT_ERROR

    def test_is_migrated_is_read_only(self):
        preprint = PreprintFactory(creator=self.admin)
        url = f'/{API_BASE}preprints/{preprint._id}/'
        res = self.app.get(url)
        assert res.json['data']['attributes']['is_migrated'] is False

        res = self.app.patch_json_api(url, self.update_payload(preprint, is_migrated=True), auth=self.admin.auth)
        assert res.status_code == 200
        preprint.reload()
        assert preprint.is_migrated is False

    def test_migrated_preprint_can_be_read(self):
        res = self.app.get(self.url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['is_migrated'] is True

        res = self.app.get(self.contributors_url)
        assert res.status_code == 200

    def test_metadata_edits_are_rejected(self):
        title = self.preprint.title
        subject = SubjectFactory()
        project = ProjectFactory(creator=self.admin)
        institution = InstitutionFactory()
        for user in [self.admin, self.write_contrib]:
            res = self.app.patch_json_api(
                self.url,
                self.update_payload(self.preprint, title='New title'),
                auth=user.auth,
                expect_errors=True
            )
            self.assert_rejected(res)

        res = self.app.patch_json_api(
            f'{self.url}relationships/subjects/',
            {'data': [{'type': 'subjects', 'id': subject._id}]},
            auth=self.admin.auth,
            expect_errors=True
        )
        self.assert_rejected(res)

        res = self.app.patch_json_api(
            f'{self.url}relationships/node/',
            {'data': {'type': 'nodes', 'id': project._id}},
            auth=self.admin.auth,
            expect_errors=True
        )
        self.assert_rejected(res)

        res = self.app.put_json_api(
            f'{self.url}relationships/institutions/',
            {'data': [{'type': 'institutions', 'id': institution._id}]},
            auth=self.admin.auth,
            expect_errors=True
        )
        self.assert_rejected(res)

        self.preprint.reload()
        assert self.preprint.title == title
        assert not self.preprint.subjects.filter(id=subject.id).exists()
        assert self.preprint.node != project
        assert not self.preprint.affiliated_institutions.filter(id=institution.id).exists()

    def test_contributor_edits_are_rejected(self):
        new_contrib = AuthUserFactory()
        res = self.app.post_json_api(
            self.contributors_url,
            {
                'data': {
                    'type': 'contributors',
                    'attributes': {
                        'bibliographic': True,
                    },
                    'relationships': {
                        'users': {
                            'data': {
                                'id': new_contrib._id,
                                'type': 'users',
                            }
                        }
                    }
                }
            },
            auth=self.admin.auth,
            expect_errors=True
        )
        self.assert_rejected(res)

        res = self.app.patch_json_api(
            self.write_contrib_url,
            self.update_contributor_payload(permission=permissions.READ),
            auth=self.admin.auth,
            expect_errors=True
        )
        self.assert_rejected(res)

        res = self.app.patch_json_api(
            self.contributors_url,
            {'data': [self.update_contributor_payload(permission=permissions.READ)['data']]},
            auth=self.admin.auth,
            expect_errors=True,
            bulk=True
        )
        self.assert_rejected(res)

        res = self.app.delete_json_api(self.write_contrib_url, auth=self.admin.auth, expect_errors=True)
        self.assert_rejected(res)

        assert not self.preprint.is_contributor(new_contrib)
        assert self.preprint.has_permission(self.write_contrib, permissions.WRITE)

    def test_new_version_is_rejected(self):
        res = self.app.post_json_api(f'{self.url}versions/?version=2.20', auth=self.admin.auth, expect_errors=True)
        self.assert_rejected(res)
        assert self.preprint.versioned_guids.first().guid.versions.count() == 1

    def test_review_actions_are_rejected(self):
        moderator = AuthUserFactory()
        self.preprint.provider.add_to_group(moderator, 'moderator')
        machine_state = self.preprint.machine_state
        for url, trigger, user in [
            (f'{self.url}review_actions/', 'submit', self.admin),
            (f'/{API_BASE}actions/reviews/', 'withdraw', moderator),
        ]:
            res = self.app.post_json_api(
                url,
                {
                    'data': {
                        'type': 'actions',
                        'attributes': {
                            'trigger': trigger,
                        },
                        'relationships': {
                            'target': {
                                'data': {
                                    'type': 'preprints',
                                    'id': self.preprint._id,
                                }
                            }
                        }
                    }
                },
                auth=user.auth,
                expect_errors=True
            )
            self.assert_rejected(res)

        self.preprint.reload()
        assert self.preprint.machine_state == machine_state
        assert not self.preprint.is_retracted

    def test_withdrawal_requests_are_rejected(self):
        res = self.app.post_json_api(
            f'{self.url}requests/',
            {
                'data': {
                    'type': 'preprint-requests',
                    'attributes': {
                        'comment': 'Please withdraw',
                        'request_type': RequestTypes.WITHDRAWAL.value,
                    },
                }
            },
            auth=self.admin.auth,
            expect_errors=True
        )
        self.assert_rejected(res)
        assert not self.preprint.requests.exists()

        moderator = AuthUserFactory()
        self.preprint.provider.add_to_group(moderator, 'moderator')
        withdrawal_request = PreprintRequestFactory(
            creator=self.admin,
            target=self.preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value
        )
        withdrawal_request.run_submit(self.admin)
        res = self.app.post_json_api(
            f'/{API_BASE}actions/requests/preprints/',
            {
                'data': {
                    'type': 'preprint-request-actions',
                    'attributes': {
                        'trigger': 'accept',
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'type': 'preprint-requests',
                                'id': withdrawal_request._id,
                            }
                        }
                    }
                }
            },
            auth=moderator.auth,
            expect_errors=True
        )
        self.assert_rejected(res)

        self.preprint.reload()
        assert not self.preprint.is_retracted
