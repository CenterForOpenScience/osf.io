import mock
import pytest

from datetime import timedelta
from django.utils import timezone

from osf_tests.factories import AuthUserFactory, ChronosJournalFactory, ChronosSubmissionFactory, PreprintFactory
from osf.utils.migrations import disable_auto_now_fields
from osf.models.chronos import ChronosSubmission
from website import settings

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
    def journal_one(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def journal_two(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def journal_three(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def other_journal(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def preprint(self, submitter, preprint_contributor, moderator):
        pp = PreprintFactory(creator=submitter)
        pp.add_contributor(preprint_contributor, save=True)
        pp.provider.get_group('moderator').user_set.add(moderator)
        return pp

    @pytest.fixture()
    def other_preprint(self, submitter, preprint):
        return PreprintFactory(creator=submitter, provider=preprint.provider)

    @pytest.fixture()
    def submission_submitted(self, preprint, journal_one, submitter):
        return ChronosSubmissionFactory(submitter=submitter, journal=journal_one, preprint=preprint, status=2)

    @pytest.fixture()
    def submission_accepted(self, preprint, journal_two, submitter):
        return ChronosSubmissionFactory(submitter=submitter, journal=journal_two, preprint=preprint, status=3)

    @pytest.fixture()
    def submission_published(self, preprint, journal_three, submitter):
        return ChronosSubmissionFactory(submitter=submitter, journal=journal_three, preprint=preprint, status=4)

    @pytest.fixture()
    def other_submission(self, other_preprint, journal_one, submitter):
        return ChronosSubmissionFactory(submitter=submitter, journal=journal_one, preprint=other_preprint)

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

    # Preprint submitters can view all submissions, regardless of states
    def test_list_submitter(self, app, url, submission_submitted, submission_accepted, submission_published, other_submission, submitter):
        res = app.get(url, auth=submitter.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 3
        submission_ids = [submission_submitted.publication_id, submission_accepted.publication_id,
                          submission_published.publication_id]
        assert res.json['data'][0]['id'] in submission_ids
        assert res.json['data'][1]['id'] in submission_ids
        assert res.json['data'][2]['id'] in submission_ids

    # Preprint contributors can view all submissions, regardless of states
    def test_list_contributor(self, app, url, submission_submitted, submission_accepted, submission_published, other_submission, preprint_contributor):
        res = app.get(url, auth=preprint_contributor.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 3
        submission_ids = [submission_submitted.publication_id, submission_accepted.publication_id,
                          submission_published.publication_id]
        assert res.json['data'][0]['id'] in submission_ids
        assert res.json['data'][1]['id'] in submission_ids
        assert res.json['data'][2]['id'] in submission_ids

    # Moderators can only see accepted and published submissions
    def test_list_moderator(self, app, url, submission_submitted, submission_accepted, submission_published, other_submission, moderator):
        res = app.get(url, auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        submission_ids = [submission_accepted.publication_id, submission_published.publication_id]
        assert res.json['data'][0]['id'] in submission_ids
        assert res.json['data'][1]['id'] in submission_ids

    # Logged in users can only see accepted and published submissions
    def test_list_user(self, app, url, submission_submitted, submission_accepted, submission_published, other_submission, user):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        submission_ids = [submission_accepted.publication_id, submission_published.publication_id]
        assert res.json['data'][0]['id'] in submission_ids
        assert res.json['data'][1]['id'] in submission_ids

    # Users with no auth can only see accepted and published submissions
    def test_list_no_auth(self, app, url, submission_submitted, submission_accepted, submission_published, other_submission):
        res = app.get(url)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        submission_ids = [submission_accepted.publication_id, submission_published.publication_id]
        assert res.json['data'][0]['id'] in submission_ids
        assert res.json['data'][1]['id'] in submission_ids


@pytest.mark.django_db
class TestChronosSubmissionAutomaticUpdate:

    @pytest.fixture()
    def submitter(self):
        return AuthUserFactory()

    @pytest.fixture()
    def journal_one(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def journal_two(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def preprint(self, submitter):
        return PreprintFactory(creator=submitter)

    @pytest.fixture()
    def submission_stale(self, preprint, journal_one, submitter):
        with disable_auto_now_fields(models=[ChronosSubmission]):
            submission = ChronosSubmission(
                submitter=submitter, journal=journal_one, preprint=preprint, status=2,
                raw_response='', publication_id='fake-publication-id-stale',
            )
            submission.modified = timezone.now() - settings.CHRONOS_SUBMISSION_UPDATE_TIME - timedelta(days=1)
            submission.save()
            return submission

    @pytest.fixture()
    def submission_fresh(self, preprint, journal_two, submitter):
        return ChronosSubmissionFactory(
            submitter=submitter, journal=journal_two,
            preprint=preprint, status=2,
            publication_id='fake-publication-id-fresh',
        )

    @pytest.fixture()
    def url(self, preprint):
        return '/_/chronos/{}/submissions/'.format(preprint._id)

    @mock.patch('api.chronos.views.enqueue_task')
    def test_enqueue_is_called_with_submission_is_stale(self, mock_enqueue, app, url, submission_stale, submitter):
        res = app.get(url, auth=submitter.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        mock_enqueue.assert_called()

    @mock.patch('api.chronos.views.enqueue_task')
    def test_enqueue_is_not_called_with_submission_is_fresh(self, mock_enqueue, app, url, submission_fresh, submitter):
        res = app.get(url, auth=submitter.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        mock_enqueue.assert_not_called()

    # @pytest.mark.enable_enqueue_task
    @mock.patch('api.chronos.views.enqueue_task')
    def test_mix_enqueue(self, mock_enqueue, app, url, submission_fresh, submission_stale, submitter):
        res = app.get(url, auth=submitter.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        from osf.external.tasks import update_submissions_status_async
        mock_enqueue.assert_called_with(update_submissions_status_async.s([submission_stale.id]))
