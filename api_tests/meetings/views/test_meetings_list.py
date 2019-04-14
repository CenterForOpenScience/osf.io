import pytest
import datetime
from django.utils import timezone

from osf_tests.factories import ConferenceFactory


@pytest.mark.django_db
class TestMeetingsList:

    @pytest.fixture()
    def meetings(self):
        return [ConferenceFactory(), ConferenceFactory(), ConferenceFactory()]

    @pytest.fixture()
    def meeting_ids(self, meetings):
        return [meeting.endpoint for meeting in meetings]

    @pytest.fixture()
    def url(self):
        return '/_/meetings/'

    @pytest.fixture()
    def res(self, app, meetings, url):
        return app.get(url)

    @pytest.fixture()
    def data(self, res):
        return res.json['data']

    def test_meeting_list(self, res, data, meeting_ids):
        assert res.status_code == 200
        assert set(meeting_ids) == set([meeting['id'] for meeting in data])


@pytest.mark.django_db
class TestMeetingListFilter:

    @pytest.fixture()
    def meeting_one(self):
        return ConferenceFactory(name='Science and Reproducibility', location='San Diego, CA', start_date=(timezone.now() - datetime.timedelta(days=1)))

    @pytest.fixture()
    def meeting_two(self):
        return ConferenceFactory(name='Open Science', location='Richmond, VA', start_date=(timezone.now() - datetime.timedelta(days=30)))

    @pytest.fixture()
    def meeting_three(self):
        return ConferenceFactory(name='Neurons', location='Charlottesville, VA', start_date=(timezone.now() - datetime.timedelta(days=5)))

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
