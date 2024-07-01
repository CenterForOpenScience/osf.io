from datetime import datetime
from unittest import mock

import pytest
import responses

from api.share.utils import shtrove_ingest_url, sharev2_push_url
from framework.auth.core import Auth
from osf.models.spam import SpamStatus
from osf.utils.permissions import READ, WRITE, ADMIN
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    SubjectFactory,
    PreprintFactory,
    PreprintProviderFactory,
)
from website import settings
from website.preprints.tasks import on_preprint_updated
from ._utils import expect_preprint_ingest_request


@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestPreprintShare:
    @pytest.fixture(scope='class', autouse=True)
    def _patches(self):
        with mock.patch.object(settings, 'USE_CELERY', False):
            yield

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def auth(self, user):
        return Auth(user=user)

    @pytest.fixture
    def provider(self):
        return PreprintProviderFactory(
            name='Lars Larson Snowmobiling Experience',
            access_token='Snowmobiling'
        )

    @pytest.fixture
    def project(self, user, mock_share_responses):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture
    def subject(self):
        return SubjectFactory(text='Subject #1')

    @pytest.fixture
    def subject_two(self):
        return SubjectFactory(text='Subject #2')

    @pytest.fixture
    def preprint(self, project, user, provider, subject):
        return PreprintFactory(
            creator=user,
            filename='second_place.pdf',
            provider=provider,
            subjects=[[subject._id]],
            project=project,
            is_published=False
        )

    def test_save_unpublished_not_called(self, mock_share_responses, preprint):
        # expecting no ingest requests (delete or otherwise)
        with expect_preprint_ingest_request(mock_share_responses, preprint, count=0):
            preprint.save()

    def test_save_published_called(self, mock_share_responses, preprint, user, auth):
        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.set_published(True, auth=auth, save=True)

    # This covers an edge case where a preprint is forced back to unpublished
    # that it sends the information back to share
    def test_save_unpublished_called_forced(self, mock_share_responses, auth, preprint):
        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.set_published(True, auth=auth, save=True)
        with expect_preprint_ingest_request(mock_share_responses, preprint, delete=True):
            preprint.is_published = False
            preprint.save(**{'force_update': True})

    def test_save_published_subject_change_called(self, mock_share_responses, auth, preprint, subject, subject_two):
        preprint.set_published(True, auth=auth, save=True)
        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.set_subjects([[subject_two._id]], auth=auth)

    def test_save_unpublished_subject_change_not_called(self, mock_share_responses, auth, preprint, subject_two):
        with expect_preprint_ingest_request(mock_share_responses, preprint, delete=True):
            preprint.set_subjects([[subject_two._id]], auth=auth)

    def test_send_to_share_is_true(self, mock_share_responses, auth, preprint):
        preprint.set_published(True, auth=auth, save=True)
        with expect_preprint_ingest_request(mock_share_responses, preprint):
            on_preprint_updated(preprint._id, saved_fields=['title'])

    def test_preprint_contributor_changes_updates_preprints_share(self, mock_share_responses, user, auth):
        preprint = PreprintFactory(is_published=True, creator=user)
        preprint.set_published(True, auth=auth, save=True)
        user2 = AuthUserFactory()

        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.add_contributor(contributor=user2, auth=auth, save=True)

        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.move_contributor(contributor=user, index=0, auth=auth, save=True)

        data = [{'id': user._id, 'permissions': ADMIN, 'visible': True},
                {'id': user2._id, 'permissions': WRITE, 'visible': False}]

        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.manage_contributors(data, auth=auth, save=True)

        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.update_contributor(user2, READ, True, auth=auth, save=True)

        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.remove_contributor(contributor=user2, auth=auth)

    @pytest.mark.skip('Synchronous retries not supported if celery >=5.0')
    def test_call_async_update_on_500_failure(self, mock_share_responses, preprint, auth):
        mock_share_responses.replace(responses.POST, shtrove_ingest_url(), status=500)
        mock_share_responses.replace(responses.POST, sharev2_push_url(), status=500)
        preprint.set_published(True, auth=auth, save=True)
        with expect_preprint_ingest_request(mock_share_responses, preprint, count=5):
            preprint.update_search()

    def test_no_call_async_update_on_400_failure(self, mock_share_responses, preprint, auth):
        mock_share_responses.replace(responses.POST, shtrove_ingest_url(), status=400)
        mock_share_responses.replace(responses.POST, sharev2_push_url(), status=400)
        preprint.set_published(True, auth=auth, save=True)
        with expect_preprint_ingest_request(mock_share_responses, preprint, count=1):
            preprint.update_search()

    def test_delete_from_share(self, mock_share_responses):
        preprint = PreprintFactory()
        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.update_search()
        preprint.date_withdrawn = datetime.now()
        preprint.save()
        with expect_preprint_ingest_request(mock_share_responses, preprint):
            preprint.update_search()
        preprint.spam_status = SpamStatus.SPAM
        preprint.save()
        with expect_preprint_ingest_request(mock_share_responses, preprint, delete=True):
            preprint.update_search()
