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
        # Author doesn't have a family_name, just a fullname
        return AuthUserFactory(fullname='Lemonade')

    @pytest.fixture()
    def meeting_one_submission(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=True, creator=user)
        meeting.submissions.add(submission)
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_one_private_submission(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=False, creator=user)
        meeting.submissions.add(submission)
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_two_submission(self, meeting_two, user):
        submission = ProjectFactory(title='Apple Juice', is_public=True, creator=user)
        meeting_two.submissions.add(submission)
        # Submission doesn't have poster/talk tag added - will get talk tag by default (second submission type)
        return submission

    @pytest.fixture()
    def meeting_two_second_submission(self, meeting_two, user_two):
        submission = ProjectFactory(title='Bananas', is_public=True, creator=user_two)
        meeting_two.submissions.add(submission)
        submission.add_tag('poster', Auth(user_two))
        return submission

    @pytest.fixture()
    def meeting_two_third_submission(self, meeting_two, user_three):
        submission = ProjectFactory(title='Cantaloupe', is_public=True, creator=user_three)
        meeting_two.submissions.add(submission)
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
        pc, _ = PageCounter.objects.get_or_create(
            _id='download:{}:{}'.format(project._id, file._id),
            resource=project.guids.first(),
            action='download',
            file=file
        )
        pc.total = download_count
        pc.save()
        return pc

    def test_meeting_submissions_list(self, app, user, meeting, url, meeting_one_submission, meeting_one_private_submission):
        api_utils.create_test_file(meeting_one_submission, user, create_guid=False)
        res = app.get(url)
        data = res.json['data']
        assert res.status_code == 200
        assert data[0]['id'] == meeting_one_submission._id
        assert data[0]['type'] == 'meeting-submissions'
        assert data[0]['attributes']['title'] == meeting_one_submission.title
        assert data[0]['attributes']['author_name'] == user.family_name
        assert 'download' in data[0]['links']
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
        res = app.get(url_meeting_two + '?filter[author_name]=Lemon')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert res.json['data'][0]['id'] == third
        assert res.json['data'][0]['attributes']['author_name'] == 'Lemonade'

        # test search meeting_meeting_category
        res = app.get(url_meeting_two + '?filter[meeting_category]=post')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2
        assert res.json['data'][0]['attributes']['meeting_category'] == 'poster'
        assert res.json['data'][1]['attributes']['meeting_category'] == 'poster'
        assert set([submission['id'] for submission in res.json['data']]) == set([second, third])

        # test search title, author, meeting_category combined (OR)
        res = app.get(url_meeting_two + '?filter[title,author_name,meeting_category]=cantaloupe')
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['title'] == 'Cantaloupe'
        assert res.json['data'][0]['id'] == third

        res = app.get(url_meeting_two + '?filter[title,author_name,meeting_category]=mcgee')
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['author_name'] == 'McGee'
        assert res.json['data'][0]['id'] == first

        res = app.get(url_meeting_two + '?filter[title,author_name,meeting_category]=talk')
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['meeting_category'] == 'talk'
        assert res.json['data'][0]['id'] == first

        res = app.get(url_meeting_two + '?filter[title,author_name,meeting_category]=juice')
        assert len(res.json['data']) == 2
        # Results include an author match and a title match
        assert set([first, second]) == set([sub['id'] for sub in res.json['data']])

        # test sort title
        res = app.get(url_meeting_two + '?sort=title')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert data[0]['id'] == first
        assert data[0]['type'] == 'meeting-submissions'
        assert data[0]['attributes']['title'] == meeting_two_submission.title
        assert data[0]['attributes']['download_count'] == 2
        assert file._id in data[0]['links']['download']

        assert data[1]['id'] == second
        assert data[1]['type'] == 'meeting-submissions'
        assert data[1]['attributes']['title'] == meeting_two_second_submission.title
        assert data[1]['attributes']['download_count'] == 1
        assert file_two._id in data[1]['links']['download']

        assert data[2]['id'] == third
        assert data[2]['type'] == 'meeting-submissions'
        assert data[2]['attributes']['title'] == meeting_two_third_submission.title
        assert data[2]['attributes']['download_count'] == 0
        assert file_three._id in data[2]['links']['download']

        # test reverse sort title
        res = app.get(url_meeting_two + '?sort=-title')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert [third, second, first] == [meeting['id'] for meeting in data]
        assert ['Cantaloupe', 'Bananas', 'Apple Juice'] == [meeting['attributes']['title'] for meeting in data]

        # test sort author
        res = app.get(url_meeting_two + '?sort=author_name')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert [second, third, first] == [meeting['id'] for meeting in data]
        assert ['Juice', 'Lemonade', 'McGee'] == [meeting['attributes']['author_name'] for meeting in data]

        # test reverse sort author
        res = app.get(url_meeting_two + '?sort=-author_name')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert [first, third, second] == [meeting['id'] for meeting in data]
        assert ['McGee', 'Lemonade', 'Juice'] == [meeting['attributes']['author_name'] for meeting in data]

        # test sort meeting_category
        res = app.get(url_meeting_two + '?sort=meeting_category')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert [second, third, first] == [meeting['id'] for meeting in data]
        assert ['poster', 'poster', 'talk'] == [meeting['attributes']['meeting_category'] for meeting in data]

        # test reverse sort meeting_category
        res = app.get(url_meeting_two + '?sort=-meeting_category')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert ['talk', 'poster', 'poster'] == [meeting['attributes']['meeting_category'] for meeting in data]

        # test sort created
        res = app.get(url_meeting_two + '?sort=created')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert [first, second, third] == [meeting['id'] for meeting in data]
        assert meeting_two_submission.created < meeting_two_second_submission.created
        assert meeting_two_second_submission.created < meeting_two_third_submission.created

        # test sort reverse created
        res = app.get(url_meeting_two + '?sort=-created')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert [third, second, first] == [meeting['id'] for meeting in data]

        # test sort download count
        res = app.get(url_meeting_two + '?sort=download_count')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert [third, second, first] == [meeting['id'] for meeting in data]
        assert [0, 1, 2] == [meeting['attributes']['download_count'] for meeting in data]

        # test reverse sort download count
        res = app.get(url_meeting_two + '?sort=-download_count')
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert [first, second, third] == [meeting['id'] for meeting in data]
        assert [2, 1, 0] == [meeting['attributes']['download_count'] for meeting in data]
