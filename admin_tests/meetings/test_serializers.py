from tests.base import AdminTestCase
from tests.test_conferences import ConferenceFactory

from admin.meetings.serializers import serialize_meeting


class TestsSerializeMeeting(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.conf = ConferenceFactory()

    def test_serialize(self):
        res = serialize_meeting(self.conf)
        assert isinstance(res, dict)
        assert res['endpoint'] == self.conf.endpoint
        assert res['name'] == self.conf.name
        assert res['info_url'] == self.conf.info_url
        assert res['logo_url'] == self.conf.logo_url
        assert res['active'] == self.conf.active
        assert res['public_projects'] == self.conf.public_projects
        assert res['poster'] == self.conf.poster
        assert res['talk'] == self.conf.talk
        assert res['num_submissions'] == self.conf.valid_submissions.count()
