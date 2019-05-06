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
    def url(self, meeting):
        return '/_/meetings/{}/submissions/'.format(meeting.endpoint)

    @pytest.fixture()
    def url_meeting_two(self, meeting_two):
        return '/_/meetings/{}/submissions/'.format(meeting_two.endpoint)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory(fullname='Grapes McGee')

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory(fullname='Orange Juice')

    @pytest.fixture()
    def user_three(self):
        return AuthUserFactory(fullname='Lemonade')

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
        submission.add_tag('talk', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_two_second_submission(self, meeting_two, user_two):
        submission = ProjectFactory(title='Bananas', is_public=True, creator=user_two)
        submission.add_tag(meeting_two.endpoint, Auth(user_two))
        submission.add_tag('poster', Auth(user_two))
        return submission

    @pytest.fixture()
    def meeting_two_third_submission(self, meeting_two, user_three):
        submission = ProjectFactory(title='Cantaloupe', is_public=True, creator=user_three)
        submission.add_tag(meeting_two.endpoint, Auth(user_three))
        submission.add_tag('poster', Auth(user_three))
        return submission

    @pytest.fixture()
    def file(self, user, meeting_two_submission):
        file = api_utils.create_test_file(meeting_two_submission, user, create_guid=False)
        self.mock_download(meeting_two_submission, file, 2)
        return file

    @pytest.fixture()
    def file_two(self, user, meeting_two_second_submission):
        file = api_utils.create_test_file(meeting_two_second_submission, user, create_guid=False)
        self.mock_download(meeting_two_second_submission, file, 1)
        return file

    @pytest.fixture()
    def file_three(self, user, meeting_two_third_submission):
        file = api_utils.create_test_file(meeting_two_third_submission, user, create_guid=False)
        return file

    def mock_download(self, project, file, download_count):
        return PageCounter.objects.create(_id='download:{}:{}'.format(project._id, file._id), total=download_count)

    def test_meeting_submissions_list(self, app, user, meeting, url, meeting_one_submission, meeting_one_private_submission):
        res = app.get(url)
        assert res.status_code == 200
        data = res.json['data']
        # meeting_one_submission does not have any associated files, so it's not included in the list
        assert len(data) == 0

        api_utils.create_test_file(meeting_one_submission, user, create_guid=False)
        res = app.get(url)
        data = res.json['data']
        assert res.status_code == 200
        assert data[0]['id'] == meeting_one_submission._id
        assert data[0]['type'] == 'meeting-submissions'
        assert data[0]['attributes']['title'] == meeting_one_submission.title
        assert data[0]['attributes']['author_name'] == user.family_name
        assert 'submission_file' in data[0]['relationships']
        assert 'author' in data[0]['relationships']

    def test_meeting_submissions_list_sorting_and_filtering(self, app, url_meeting_two, meeting_two,
            meeting_two_submission, file, meeting_two_second_submission, file_two, meeting_two_third_submission, file_three):
        first = meeting_two_submission._id
        second = meeting_two_second_submission._id
        third = meeting_two_third_submission._id

        # test search title
        res = app.get(url_meeting_two + '?filter[title]=Apple')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert res.json['data'][0]['id'] == first

        # test search author

        # test search category

        # test search title, author, category combined

        # test sort title
        res = app.get(url_meeting_two + '?sort=title')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert data[0]['id'] == first
        assert data[0]['type'] == 'meeting-submissions'
        assert data[0]['attributes']['title'] == meeting_two_submission.title
        assert data[0]['attributes']['download_count'] == 2
        assert data[0]['relationships']['submission_file']['data']['id'] == file._id

        assert data[1]['id'] == second
        assert data[1]['type'] == 'meeting-submissions'
        assert data[1]['attributes']['title'] == meeting_two_second_submission.title
        assert data[1]['attributes']['download_count'] == 1
        assert data[1]['relationships']['submission_file']['data']['id'] == file_two._id

        assert data[2]['id'] == third
        assert data[2]['type'] == 'meeting-submissions'
        assert data[2]['attributes']['title'] == meeting_two_third_submission.title
        assert data[2]['attributes']['download_count'] == 0
        assert data[2]['relationships']['submission_file']['data']['id'] == file_three._id

        # test reverse sort title
        res = app.get(url_meeting_two + '?sort=-title')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([first, second, third]) == set([meeting['id'] for meeting in data])
        assert set(['Cantaloupe', 'Bananas', 'Apples']) == set([meeting['attributes']['title'] for meeting in data])

        # test sort author
        res = app.get(url_meeting_two + '?sort=author_name')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([second, third, first]) == set([meeting['id'] for meeting in data])
        assert set(['Juice', 'Lemonade', 'McGee']) == set([meeting['attributes']['author_name'] for meeting in data])

        # test reverse sort author
        res = app.get(url_meeting_two + '?sort=-author_name')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([first, third, second]) == set([meeting['id'] for meeting in data])
        assert set(['McGee', 'Lemonade', 'Juice']) == set([meeting['attributes']['author_name'] for meeting in data])

        # test sort category
        res = app.get(url_meeting_two + '?sort=category')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([second, third, first]) == set([meeting['id'] for meeting in data])
        assert set(['poster', 'poster', 'talk']) == set([meeting['attributes']['category'] for meeting in data])

        # test reverse sort category
        res = app.get(url_meeting_two + '?sort=-category')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([first, third, second]) == set([meeting['id'] for meeting in data])
        assert set(['talk', 'poster', 'poster']) == set([meeting['attributes']['category'] for meeting in data])

        # test sort created
        res = app.get(url_meeting_two + '?sort=date_created')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([first, second, third]) == set([meeting['id'] for meeting in data])
        assert meeting_two_submission.created < meeting_two_second_submission.created
        assert meeting_two_second_submission.created < meeting_two_third_submission.created

        # test sort reverse created
        res = app.get(url_meeting_two + '?sort=-date_created')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([third, second, first]) == set([meeting['id'] for meeting in data])

        # test sort download count
        res = app.get(url_meeting_two + '?sort=download_count')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([third, second, first]) == set([meeting['id'] for meeting in data])
        assert set([0, 1, 2]) == set([meeting['attributes']['download_count'] for meeting in data])

        # test reverse sort download count
        res = app.get(url_meeting_two + '?sort=-download_count')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([first, second, third]) == set([meeting['id'] for meeting in data])
        assert set([2, 1, 0]) == set([meeting['attributes']['download_count'] for meeting in data])
