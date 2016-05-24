from nose import tools as nt

from tests.base import AdminTestCase
from tests.test_conferences import ConferenceFactory

from admin.meetings.serializers import serialize_meeting


class TestsSerializeMeeting(AdminTestCase):
    def setUp(self):
        super(TestsSerializeMeeting, self).setUp()
        self.conf = ConferenceFactory()

    def test_serialize(self):
        res = serialize_meeting(self.conf)
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['endpoint'], self.conf.endpoint)
        nt.assert_equal(res['name'], self.conf.name)
        nt.assert_equal(res['info_url'], self.conf.info_url)
        nt.assert_equal(res['logo_url'], self.conf.logo_url)
        nt.assert_equal(res['active'], self.conf.active)
        nt.assert_equal(res['public_projects'], self.conf.public_projects)
        nt.assert_equal(res['poster'], self.conf.poster)
        nt.assert_equal(res['talk'], self.conf.talk)
        nt.assert_equal(res['num_submissions'], self.conf.num_submissions)
