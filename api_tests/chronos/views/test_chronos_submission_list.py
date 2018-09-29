import mock
import pytest

from osf_tests.factories import AuthUserFactory, ChronosJournalFactory, ChronosSubmissionFactory, PreprintFactory


@pytest.mark.django_db
class TestChronosSubmissionList:

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
    def other_journal(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def preprint(self, submitter, preprint_contributor, moderator):
        pp = PreprintFactory(creator=submitter)
        pp.node.add_contributor(preprint_contributor, save=True)
        pp.provider.get_group('moderator').user_set.add(moderator)
        return pp

    @pytest.fixture()
    def other_preprint(self, submitter, preprint):
        return PreprintFactory(creator=submitter, provider=preprint.provider)

    @pytest.fixture()
    def submission(self, preprint, journal, submitter):
        return ChronosSubmissionFactory(submitter=submitter, journal=journal, preprint=preprint)

    @pytest.fixture()
    def other_submission(self, other_preprint, journal, submitter):
        return ChronosSubmissionFactory(submitter=submitter, journal=journal, preprint=other_preprint)

    @pytest.fixture()
    def url(self, preprint):
        return '/_/chronos/{}/submissions/'.format(preprint._id)

    def create_payload(self, journal):
        return {
            'data': {
                'attributes': {},
                'type': 'chronos-submissions',
                'relationships': {
                    'journal': {
                        'data': {
                            'id': journal.journal_id,
                            'type': 'chronos-journals',
                        }
                    }
                }
            }
        }

    @mock.patch('api.chronos.serializers.ChronosClient.submit_manuscript', wraps=ChronosSubmissionFactory.create)
    def test_create_success(self, mock_submit, app, url, other_journal, submitter, preprint):
        payload = self.create_payload(other_journal)
        res = app.post_json_api(url, payload, auth=submitter.auth)
        assert res.status_code == 201
        assert mock_submit.called
        mock_submit.assert_called_once_with(journal=other_journal, submitter=submitter, preprint=preprint)

    @mock.patch('api.chronos.serializers.ChronosClient.submit_manuscript', wraps=ChronosSubmissionFactory.create)
    def test_create_failure(self, mock_submit, app, url, other_journal, preprint_contributor, moderator, user):
        payload = self.create_payload(other_journal)
        res = app.post_json_api(url, payload, auth=preprint_contributor.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.post_json_api(url, payload, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        assert not mock_submit.called

    def test_list(self, app, url, submission, other_submission):
        res = app.get(url)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == submission.publication_id
