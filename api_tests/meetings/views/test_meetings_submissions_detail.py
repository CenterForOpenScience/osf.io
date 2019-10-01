import pytest

from api_tests import utils as api_utils

from framework.auth.core import Auth
from osf.models import PageCounter
from osf_tests.factories import ConferenceFactory, ProjectFactory, AuthUserFactory


@pytest.mark.django_db
class TestMeetingSubmissionsDetail:

    @pytest.fixture()
    def meeting(self):
        return ConferenceFactory(name='OSF 2019', endpoint='osf2019')

    @pytest.fixture()
    def base_url(self, meeting):
        return '/_/meetings/{}/submissions/'.format(meeting.endpoint)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory(fullname='Grapes McGee')

    @pytest.fixture()
    def meeting_one_submission(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=True, creator=user)
        meeting.submissions.add(submission)
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_submission_no_category(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=True, creator=user)
        meeting.submissions.add(submission)
        api_utils.create_test_file(submission, user, create_guid=False)
        return submission

    @pytest.fixture()
    def meeting_one_private_submission(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=False, creator=user)
        meeting.submissions.add(submission)
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def random_project(self, meeting, user):
        project = ProjectFactory(title='Submission One', is_public=True, creator=user)
        project.add_tag('poster', Auth(user))
        return project

    @pytest.fixture()
    def file(self, user, meeting_one_submission):
        file = api_utils.create_test_file(meeting_one_submission, user, create_guid=False)
        self.mock_download(meeting_one_submission, file, 10)
        return file

    def mock_download(self, project, file, download_count):
        pc, _ = PageCounter.objects.get_or_create(
            _id='download:{}:{}'.format(project._id, file._id),
            resource=project.guids.first(),
            action='download',
            file=file
        )
        pc.total = download_count
        pc.save()
        return pc

    def test_meeting_submission_detail(self, app, user, meeting, base_url, meeting_one_submission,
            meeting_one_private_submission, random_project, meeting_submission_no_category, file):

        # test_get_poster_submission
        url = '{}{}/'.format(base_url, meeting_one_submission._id)
        res = app.get(url)
        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == meeting_one_submission._id
        assert data['type'] == 'meeting-submissions'
        assert data['attributes']['title'] == meeting_one_submission.title
        assert data['attributes']['author_name'] == user.family_name
        assert data['attributes']['download_count'] == 10
        assert 'date_created' in data['attributes']
        assert data['attributes']['meeting_category'] == 'poster'
        assert '/_/meetings/{}/submissions/{}'.format(meeting.endpoint, meeting_one_submission._id) in data['links']['self']
        assert data['relationships']['author']['data']['id'] == user._id
        assert file._id in data['links']['download']

        # test_get_private_submission
        url = '{}{}/'.format(base_url, meeting_one_private_submission._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # Restricting even logged in contributor from viewing private submission
        url = '{}{}/'.format(base_url, meeting_one_private_submission._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

        # test_get_random_project_not_affiliated_with_meeting
        url = '{}{}/'.format(base_url, random_project._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'This is not a submission to OSF 2019.'

        # test_get_invalid_submission
        url = '{}{}/'.format(base_url, 'jjjjj')
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

        # test_get_meeting_submission_with_no_category
        url = '{}{}/'.format(base_url, meeting_submission_no_category._id)
        res = app.get(url)
        assert res.status_code == 200
        # Second submission type given by default if none exists (following legacy logic)
        assert res.json['data']['attributes']['meeting_category'] == 'talk'
