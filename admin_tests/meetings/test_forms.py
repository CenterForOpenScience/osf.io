from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory
from tests.test_conferences import ConferenceFactory

from admin.meetings.forms import MeetingForm, MultiEmailField

data = dict(
    edit='False',
    endpoint='short',
    name='Much longer',
    info_url='http://something.com',
    logo_url='http://osf.io/eg634',
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
    homepage_link_text='Need to add to tests',
)


class TestMultiEmailField(AdminTestCase):
    def test_to_python_nothing(self):
        field = MultiEmailField()
        res = field.to_python('')
        assert res == []

    def test_to_python_one(self):
        field = MultiEmailField()
        res = field.to_python('aaa@email.org')
        assert res == ['aaa@email.org']

    def test_to_python_more(self):
        field = MultiEmailField()
        res = field.to_python('aaa@email.org, bbb@email.org, ccc@email.org')
        assert res == ['aaa@email.org', 'bbb@email.org', 'ccc@email.org']


class TestMeetingForm(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()

    def test_clean_admins_raise(self):
        form = MeetingForm(data=data)
        assert not form.is_valid()
        assert 'admins' in form.errors
        assert 'zzz@email.org' in form.errors['admins'][0]
        assert 'does not have an OSF account' in form.errors['admins'][0]

    def test_clean_admins_okay(self):
        mod_data = dict(data)
        mod_data.update({'admins': self.user.emails.values_list('address', flat=True).first()})
        form = MeetingForm(data=mod_data)
        assert form.is_valid()

    def test_clean_endpoint_raise_not_exist(self):
        mod_data = dict(data)
        mod_data.update({'admins': self.user.emails.values_list('address', flat=True).first(), 'edit': 'True'})
        form = MeetingForm(data=mod_data)
        assert 'endpoint' in form.errors
        assert 'Meeting not found with this endpoint to update' == form.errors['endpoint'][0]

    def test_clean_endpoint_raise_exists(self):
        conf = ConferenceFactory()
        mod_data = dict(data)
        mod_data.update({'admins': self.user.emails.values_list('address', flat=True).first(),
                         'endpoint': conf.endpoint})
        form = MeetingForm(data=mod_data)
        assert 'endpoint' in form.errors
        assert 'A meeting with this endpoint exists already.' == form.errors['endpoint'][0]
