import pytest
import datetime
from django.utils import timezone
from framework.auth.core import Auth

from osf_tests.factories import ConferenceFactory, ProjectFactory, AuthUserFactory

def create_eligible_conference(active=True):
    conference = ConferenceFactory(active=active)
    for i in range(0, 5):
        project = ProjectFactory(is_public=True)
        project.add_tag(conference.endpoint, Auth(project.creator))
        project.save()
    return conference

@pytest.mark.django_db
class TestMeetingsList:

    @pytest.fixture()
    def meeting_one(self):
        return ConferenceFactory()

    @pytest.fixture()
    def meeting_two(self):
        return create_eligible_conference()

    @pytest.fixture()
    def meeting_three(self):
        return create_eligible_conference()

    @pytest.fixture()
    def url(self):
        return '/_/meetings/'

    @pytest.fixture()
    def res(self, app, meeting_one, meeting_two, meeting_three, url):
        return app.get(url)

    def test_meeting_list(self, res, meeting_one, meeting_two, meeting_three):
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert set([meeting['id']for meeting in res.json['data']]) == set([meeting_two.endpoint, meeting_three.endpoint])


@pytest.mark.django_db
class TestMeetingListFilter:

    @pytest.fixture()
    def meeting_one(self):
        # Will have 6 submissions total
        conference = create_eligible_conference()
        conference.name = 'Science and Reproducibility'
        conference.location = 'San Diego, CA'
        conference.start_date = (timezone.now() - datetime.timedelta(days=1))
        conference.save()
        return conference

    @pytest.fixture()
    def meeting_two(self):
        # Will have 5 submissions total
        conference = create_eligible_conference()
        conference.name = 'Open Science'
        conference.location = 'Richmond, VA'
        conference.start_date = (timezone.now() - datetime.timedelta(days=30))
        conference.save()
        return conference

    @pytest.fixture()
    def meeting_three(self):
        # Will have 7 submissions total
        conference = create_eligible_conference()
        conference.name = 'Neurons'
        conference.location = 'Charlottesville, VA'
        conference.start_date = (timezone.now() - datetime.timedelta(days=5))
        conference.save()
        return conference

    @pytest.fixture()
    def meeting_one_submission(self, meeting_one, user):
        submission = ProjectFactory(is_public=True, creator=user)
        submission.add_tag(meeting_one.endpoint, Auth(user))
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_three_submission_one(self, meeting_one, user):
        submission = ProjectFactory(is_public=True, creator=user)
        submission.add_tag(meeting_one.endpoint, Auth(user))
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def meeting_three_submission_two(self, meeting_three, user):
        submission = ProjectFactory(is_public=True, creator=user)
        submission.add_tag(meeting_three.endpoint, Auth(user))
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def filter_url(self):
        return '/_/meetings/?filter'

    @pytest.fixture()
    def sort_url(self):
        return '/_/meetings/?sort='

    def test_meeting_list_filter(self, app, meeting_one, meeting_two, meeting_three, filter_url, sort_url):
        # Filter on name
        res = app.get('{}{}'.format(filter_url, '[name]=Science'))
        assert len(res.json['data']) == 2
        assert set([meeting_one.endpoint, meeting_two.endpoint]) == set([meeting['id'] for meeting in res.json['data']])

        res = app.get('{}{}'.format(filter_url, '[name]=Neurons'))
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == meeting_three.endpoint

        res = app.get('{}{}'.format(filter_url, '[name]=no match'))
        assert len(res.json['data']) == 0

        # Sort on name
        res = app.get('{}{}'.format(sort_url, 'name'))
        assert len(res.json['data']) == 3
        assert set([meeting_three.endpoint, meeting_two.endpoint, meeting_one.endpoint]) == set([meeting['id'] for meeting in res.json['data']])

        # Reverse sort name
        res = app.get('{}{}'.format(sort_url, '-name'))
        assert len(res.json['data']) == 3
        assert set([meeting_one.endpoint, meeting_two.endpoint, meeting_three.endpoint]) == set([meeting['id'] for meeting in res.json['data']])

        # Sort on location
        res = app.get('{}{}'.format(sort_url, 'location'))
        assert len(res.json['data']) == 3
        assert set([meeting_three.endpoint, meeting_two.endpoint, meeting_one.endpoint]) == set([meeting['id'] for meeting in res.json['data']])

        # Reverse sort location
        res = app.get('{}{}'.format(sort_url, '-location'))
        assert len(res.json['data']) == 3
        assert set([meeting_one.endpoint, meeting_two.endpoint, meeting_three.endpoint]) == set([meeting['id'] for meeting in res.json['data']])

        # Sort on start date
        res = app.get('{}{}'.format(sort_url, 'start_date'))
        assert len(res.json['data']) == 3
        assert set([meeting_two.endpoint, meeting_three.endpoint, meeting_one.endpoint]) == set([meeting['id'] for meeting in res.json['data']])

        # Sort on reverse start date
        res = app.get('{}{}'.format(sort_url, '-start_date'))
        assert len(res.json['data']) == 3
        assert set([meeting_one.endpoint, meeting_three.endpoint, meeting_two.endpoint]) == set([meeting['id'] for meeting in res.json['data']])

        # Sort on submissions count
        res = app.get('{}{}'.format(sort_url, 'num_submissions'))
        assert len(res.json['data']) == 3
        assert set([meeting_two.endpoint, meeting_one.endpoint, meeting_three.endpoint]) == set([meeting['id'] for meeting in res.json['data']])

        # Reverse sort on submissions count
        res = app.get('{}{}'.format(sort_url, '-num_submissions'))
        assert len(res.json['data']) == 3
        assert set([meeting_three.endpoint, meeting_one.endpoint, meeting_two.endpoint]) == set([meeting['id'] for meeting in res.json['data']])
