from nose import tools as nt

from tests.base import AdminTestCase
from tests.factories import AuthUserFactory
from tests.test_conferences import ConferenceFactory

from admin.meetings.forms import MeetingForm, MultiEmailField


data = dict(
    edit='False',
    endpoint='short',
    name='Much longer',
    info_url='www.something.com',
    logo_url='osf.io/eg634',
    active='True',
    admins='zzz@email.org',
    public_projects='True',
    poster='True',
    talk='True',
    submission1='poster',
    submission2='talk',
    submission1_plural='posters',
    submission2_plural='talks',
    meeting_title_type='Of course',
    add_submission='No more',
    mail_subject='Awesome',
    mail_message_body='Nothings',
    mail_attachment='Again',
)


class TestMultiEmailField(AdminTestCase):
    def test_to_python_nothing(self):
        field = MultiEmailField()
        res = field.to_python('')
        nt.assert_equal(res, [])

    def test_to_python_one(self):
        field = MultiEmailField()
        res = field.to_python('aaa@email.org')
        nt.assert_equal(res, ['aaa@email.org'])

    def test_to_python_more(self):
        field = MultiEmailField()
        res = field.to_python('aaa@email.org, bbb@email.org, ccc@email.org')
        nt.assert_equal(res,
                        ['aaa@email.org', 'bbb@email.org', 'ccc@email.org'])


class TestMeetingForm(AdminTestCase):
    def setUp(self):
        super(TestMeetingForm, self).setUp()
        self.user = AuthUserFactory()

    def test_clean_admins_raise(self):
        form = MeetingForm(data=data)
        nt.assert_false(form.is_valid())
        nt.assert_in('admins', form.errors)
        nt.assert_in('zzz@email.org', form.errors['admins'][0])
        nt.assert_in('does not have an OSF account', form.errors['admins'][0])

    def test_clean_admins_okay(self):
        mod_data = dict(data)
        mod_data.update({'admins': self.user.emails[0]})
        form = MeetingForm(data=mod_data)
        nt.assert_true(form.is_valid())

    def test_clean_endpoint_raise_not_exist(self):
        mod_data = dict(data)
        mod_data.update({'admins': self.user.emails[0], 'edit': 'True'})
        form = MeetingForm(data=mod_data)
        nt.assert_in('endpoint', form.errors)
        nt.assert_equal('Meeting not found with this endpoint to update',
                        form.errors['endpoint'][0])

    def test_clean_endpoint_raise_exists(self):
        conf = ConferenceFactory()
        mod_data = dict(data)
        mod_data.update({'admins': self.user.emails[0],
                         'endpoint': conf.endpoint})
        form = MeetingForm(data=mod_data)
        nt.assert_in('endpoint', form.errors)
        nt.assert_equal('A meeting with this endpoint exists already.',
                        form.errors['endpoint'][0])
