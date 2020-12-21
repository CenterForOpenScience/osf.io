from datetime import datetime
import json
import mock
import pytest
import responses

from api.share.utils import update_share

from api_tests.utils import create_test_file

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


@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestPreprintShare:

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
    def project(self, user, mock_share):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture
    def subject(self):
        return SubjectFactory(text='Subject #1')

    @pytest.fixture
    def subject_two(self):
        return SubjectFactory(text='Subject #2')

    @pytest.fixture
    def file(self, project, user):
        return create_test_file(project, user, 'second_place.pdf')

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

    def test_save_unpublished_not_called(self, mock_share, preprint):
        mock_share.reset()  # if the call is not made responses would raise an assertion error, if not reset.
        preprint.save()
        assert not len(mock_share.calls)

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_published_called(self, mock_on_preprint_updated, preprint, user, auth):
        preprint.set_published(True, auth=auth, save=True)
        assert mock_on_preprint_updated.called

    # This covers an edge case where a preprint is forced back to unpublished
    # that it sends the information back to share
    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_unpublished_called_forced(self, mock_on_preprint_updated, auth, preprint):
        preprint.set_published(True, auth=auth, save=True)
        preprint.is_published = False
        preprint.save(**{'force_update': True})
        assert mock_on_preprint_updated.call_count == 2

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_published_subject_change_called(self, mock_on_preprint_updated, auth, preprint, subject, subject_two):
        preprint.is_published = True
        preprint.set_subjects([[subject_two._id]], auth=auth)
        assert mock_on_preprint_updated.called
        call_args, call_kwargs = mock_on_preprint_updated.call_args
        assert 'old_subjects' in mock_on_preprint_updated.call_args[1]
        assert call_kwargs.get('old_subjects') == [subject.id]
        assert [subject.id] in mock_on_preprint_updated.call_args[1].values()

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_save_unpublished_subject_change_not_called(self, mock_on_preprint_updated, auth, preprint, subject_two):
        preprint.set_subjects([[subject_two._id]], auth=auth)
        assert not mock_on_preprint_updated.called

    def test_send_to_share_is_true(self, mock_share, preprint):
        on_preprint_updated(preprint._id)

        data = json.loads(mock_share.calls[-1].request.body.decode())
        assert data['data']['attributes']['data']['@graph']
        assert mock_share.calls[-1].request.headers['Authorization'] == 'Bearer Snowmobiling'

    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_preprint_contributor_changes_updates_preprints_share(self, mock_on_preprint_updated, user, file, auth):
        preprint = PreprintFactory(is_published=True, creator=user)
        assert mock_on_preprint_updated.call_count == 2

        user2 = AuthUserFactory()
        preprint.primary_file = file

        preprint.add_contributor(contributor=user2, auth=auth, save=True)
        assert mock_on_preprint_updated.call_count == 5

        preprint.move_contributor(contributor=user, index=0, auth=auth, save=True)
        assert mock_on_preprint_updated.call_count == 7

        data = [{'id': user._id, 'permissions': ADMIN, 'visible': True},
                {'id': user2._id, 'permissions': WRITE, 'visible': False}]

        preprint.manage_contributors(data, auth=auth, save=True)
        assert mock_on_preprint_updated.call_count == 9

        preprint.update_contributor(user2, READ, True, auth=auth, save=True)
        assert mock_on_preprint_updated.call_count == 11

        preprint.remove_contributor(contributor=user2, auth=auth)
        assert mock_on_preprint_updated.call_count == 13

    def test_call_async_update_on_500_failure(self, mock_share, preprint):
        mock_share.replace(responses.POST, f'{settings.SHARE_URL}api/v2/normalizeddata/', status=500)

        mock_share._calls.reset()  # reset after factory calls
        update_share(preprint)

        assert len(mock_share.calls) == 6  # first request and five retries
        data = json.loads(mock_share.calls[0].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        data = next(data for data in graph if data['@type'] == 'preprint')
        assert data['title'] == preprint.title

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        data = next(data for data in graph if data['@type'] == 'preprint')
        assert data['title'] == preprint.title

    def test_no_call_async_update_on_400_failure(self, mock_share, preprint):
        mock_share.replace(responses.POST, f'{settings.SHARE_URL}api/v2/normalizeddata/', status=400)

        mock_share._calls.reset()  # reset after factory calls
        update_share(preprint)

        assert len(mock_share.calls) == 1
        data = json.loads(mock_share.calls[0].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        data = next(data for data in graph if data['@type'] == 'preprint')
        assert data['title'] == preprint.title

    def test_delete_from_share(self, mock_share):
        preprint = PreprintFactory()
        update_share(preprint)

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        share_preprint = next(n for n in graph if n['@type'] == 'preprint')
        assert not share_preprint['is_deleted']

        preprint.date_withdrawn = datetime.now()
        update_share(preprint)

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        share_preprint = next(n for n in graph if n['@type'] == 'preprint')
        assert not share_preprint['is_deleted']

        preprint.spam_status = SpamStatus.SPAM
        update_share(preprint)

        data = json.loads(mock_share.calls[-1].request.body.decode())
        graph = data['data']['attributes']['data']['@graph']
        share_preprint = next(n for n in graph if n['@type'] == 'preprint')
        assert share_preprint['is_deleted']
