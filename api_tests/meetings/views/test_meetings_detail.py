import pytest

from framework.auth.core import Auth
from osf_tests.factories import ConferenceFactory, ProjectFactory, AuthUserFactory


@pytest.mark.django_db
class TestMeetingDetail:

    @pytest.fixture()
    def meeting(self):
        return ConferenceFactory(
            name='OSF 2019',
            endpoint='osf2019',
            location='Boulder, CO'
        )

    @pytest.fixture()
    def url(self, meeting):
        return '/_/meetings/{}/?related_counts=submissions'.format(meeting.endpoint)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def meeting_submission_one(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=True)
        submission.add_tag(meeting.endpoint, Auth(user))
        submission.add_tag('poster', Auth(user))
        return submission

    @pytest.fixture()
    def private_meeting_submission(self, meeting, user):
        submission = ProjectFactory(title='Submission One', is_public=False)
        submission.add_tag(meeting.endpoint, Auth(user))
        submission.add_tag('poster', Auth(user))
        return submission

    def test_meeting_detail(self, app, meeting, url, meeting_submission_one, private_meeting_submission):
        res = app.get(url)
        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == meeting.endpoint
        assert data['type'] == 'meetings'
        assert data['attributes']['name'] == meeting.name
        assert data['attributes']['submission_1_email'] == 'osf2019-poster@osf.io'
        assert data['attributes']['submission_2_email'] == 'osf2019-talk@osf.io'
        assert data['attributes']['num_submissions'] == 1
        assert data['attributes']['location'] == 'Boulder, CO'
        assert 'start_date' in data['attributes']
        assert 'end_date' in data['attributes']
        assert data['attributes']['active'] is True
        assert data['attributes']['field_names']['submission1'] == 'poster'
        assert data['attributes']['field_names']['submission2'] == 'talk'
        assert '_/meetings/{}/'.format(meeting.endpoint) in data['links']['self']
        assert '_/meetings/{}/submissions'.format(meeting.endpoint) in data['relationships']['submissions']['links']['related']['href']

        # Inactive meetings do not serialize submission emails
        meeting.active = False
        meeting.save()

        res = app.get(url)
        data = res.json['data']
        assert data['attributes']['submission_1_email'] == ''
        assert data['attributes']['submission_2_email'] == ''
        assert data['attributes']['active'] is False
