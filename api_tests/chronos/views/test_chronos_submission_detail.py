import mock
import pytest

from osf_tests.factories import AuthUserFactory, ChronosJournalFactory, ChronosSubmissionFactory, PreprintFactory


@pytest.mark.django_db
class TestChronosSubmissionDetail:

    @pytest.fixture()
    def submitter(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def moderator(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def journal(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def preprint(self, submitter, preprint_contributor, moderator):
        pp = PreprintFactory(creator=submitter)
        pp.add_contributor(preprint_contributor, save=True)
        pp.provider.get_group('moderator').user_set.add(moderator)
        return pp

    @pytest.fixture()
    def submission(self, preprint, journal, submitter):
        return ChronosSubmissionFactory(submitter=submitter, journal=journal, preprint=preprint, status=2)

    @pytest.fixture()
    def url(self, preprint, submission):
        return '/_/chronos/{}/submissions/{}/'.format(preprint._id, submission.publication_id)

    def update_payload(self, submission, **attrs):
        return {
            'data': {
                'attributes': attrs,
                'type': 'chronos-submissions',
                'id': submission.publication_id
            }
        }

    @mock.patch('api.chronos.serializers.ChronosClient.update_manuscript')
    def test_update_success(self, mock_update, app, url, submission, submitter):
        mock_update.return_value = submission
        payload = self.update_payload(submission)
        res = app.patch_json_api(url, payload, auth=submitter.auth)
        assert res.status_code == 200
        assert mock_update.called
        mock_update.assert_called_once_with(submission)

    @mock.patch('api.chronos.serializers.ChronosClient.update_manuscript')
    def test_update_failure(self, mock_update, app, url, submission, preprint_contributor, moderator, user):
        mock_update.return_value = submission
        payload = self.update_payload(submission)
        res = app.patch_json_api(url, payload, auth=preprint_contributor.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.patch_json_api(url, payload, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401
        assert not mock_update.called

    def test_get(self, app, url, submission, submitter, preprint_contributor, moderator, user):
        # Published
        res = app.get(url, auth=submitter.auth)
        assert res.status_code == 200

        # Reverse lookups is weird with non-uniform versioning schemes, ensure correctness
        assert '/v2/users/{}/'.format(submission.submitter._id) in res.json['data']['relationships']['submitter']['links']['related']['href']
        assert '/v2/preprints/{}/'.format(submission.preprint._id) in res.json['data']['relationships']['preprint']['links']['related']['href']
        assert '/_/chronos/journals/{}/'.format(submission.journal.journal_id, submission.publication_id) in res.json['data']['relationships']['journal']['links']['related']['href']

        res = app.get(url, auth=preprint_contributor.auth)
        assert res.status_code == 200
        res = app.get(url, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 404
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

        # Unpublished
        submission.preprint.is_published = False
        submission.preprint.date_published = None
        submission.preprint.save()

        res = app.get(url, auth=submitter.auth)
        assert res.status_code == 200
        res = app.get(url, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 404
        res = app.get(url, auth=preprint_contributor.auth, expect_errors=True)
        assert res.status_code == 200
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404
