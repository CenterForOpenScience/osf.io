import pytest

from framework.auth.core import Auth
from osf_tests.factories import ConferenceFactory, ProjectFactory, AuthUserFactory


@pytest.mark.django_db
class TestMeetingDetail:

    @pytest.fixture()
    def meeting(self):
        return ConferenceFactory(name='OSF 2019', endpoint='osf2019')

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
        assert data['relationships']['submissions']['links']['related']['meta']['count'] == 1
