import pytest

from api_tests import utils as api_utils

from framework.auth.core import Auth
from osf.models import PageCounter
from osf_tests.factories import ConferenceFactory, ProjectFactory, AuthUserFactory


@pytest.mark.django_db
class TestMeetingSubmissionsList:

    @pytest.fixture()
    def meeting(self):
        return ConferenceFactory(name='OSF 2019', endpoint='osf2019')

    @pytest.fixture()
    def meeting_two(self):
        return ConferenceFactory()

    @pytest.fixture()
    def url(self, meeting, spare_fieldsets_query):
        # Using sparse field sets - a meeting submission is technically a project, but we don't need to return all the node fields
        return '/_/meetings/{}/submissions/{}'.format(meeting.endpoint, spare_fieldsets_query)

    @pytest.fixture()
    def url_meeting_two(self, meeting_two, spare_fieldsets_query):
        return '/_/meetings/{}/submissions/{}'.format(meeting_two.endpoint, spare_fieldsets_query)

    @pytest.fixture()
    def spare_fieldsets_query(self):
        return '?fields[nodes]=tags,title,contributors,date_created,submission_download_count,meeting_submission'

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def meeting_one_submission(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=True, creator=user)
        submission.add_tag(meeting.endpoint, Auth(user))
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_one_private_submission(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=False, creator=user)
        submission.add_tag(meeting.endpoint, Auth(user))
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_two_submission(self, meeting_two, user):
        submission = ProjectFactory(title='Apples', is_public=True, creator=user)
        submission.add_tag(meeting_two.endpoint, Auth(user))
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_two_second_submission(self, meeting_two, user):
        submission = ProjectFactory(title='Bananas', is_public=True, creator=user)
        submission.add_tag(meeting_two.endpoint, Auth(user))
        submission.add_tag('talk', Auth(user))
        return submission

    @pytest.fixture()
    def file(self, user, meeting_two_submission):
        file = api_utils.create_test_file(meeting_two_submission, user, create_guid=False)
        self.mock_download(meeting_two_submission, file, 2)
        return file

    @pytest.fixture()
    def file_two(self, user, meeting_two_second_submission):
        return api_utils.create_test_file(meeting_two_second_submission, user, create_guid=False)

    def mock_download(self, project, file, download_count):
        return PageCounter.objects.create(_id='download:{}:{}'.format(project._id, file._id), total=download_count)

    def test_meeting_submissions_list(self, app, meeting, url, meeting_one_submission, meeting_one_private_submission):
        res = app.get(url)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['id'] == meeting_one_submission._id
        assert data[0]['type'] == 'nodes'
        assert data[0]['attributes']['title'] == meeting_one_submission.title
        assert 'meeting_submission' not in data[0]['relationships']

    def test_meeting_submissions_list_sorting_and_filtering(self, app, url_meeting_two, meeting_two, meeting_two_submission, file, meeting_two_second_submission, file_two):
        # test sort title
        res = app.get(url_meeting_two + '&sort=title')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2
        assert data[0]['id'] == meeting_two_submission._id
        assert data[0]['type'] == 'nodes'
        assert data[0]['attributes']['title'] == meeting_two_submission.title
        assert data[0]['relationships']['meeting_submission']['data']['id'] == file._id
        assert data[0]['relationships']['meeting_submission']['links']['related']['meta']['download_count'] == 2

        assert data[1]['id'] == meeting_two_second_submission._id
        assert data[1]['type'] == 'nodes'
        assert data[1]['attributes']['title'] == meeting_two_second_submission.title
        assert data[1]['relationships']['meeting_submission']['data']['id'] == file_two._id
        assert data[1]['relationships']['meeting_submission']['links']['related']['meta']['download_count'] == 0

        # test search title
        res = app.get(url_meeting_two + '&filter[title]=Apple')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert res.json['data'][0]['id'] == meeting_two_submission._id

        # test search category (actually tags)
        res = app.get(url_meeting_two + '&filter[tags]=poster')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert res.json['data'][0]['id'] == meeting_two_submission._id

        res = app.get(url_meeting_two + '&filter[tags]=talk')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert res.json['data'][0]['id'] == meeting_two_second_submission._id
