import json

import mock
import pytest
from nose import tools as nt
from osf.models import UserExtendedData
from osf_tests.factories import AuthUserFactory
from tests.base import (fake)
from tests.base import OsfTestCase
from website.profile import views as website_view
from website.profile.views import append_idp_attr_common
from website.util import api_url_for

pytestmark = pytest.mark.django_db


class TestUserProfileExtend(OsfTestCase):

    def setUp(self):
        super(TestUserProfileExtend, self).setUp()
        self.user = AuthUserFactory()

    def test_serialize_social_with_erad(self):
        user2 = AuthUserFactory()
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io']
        self.user.social['erad'] = '123'
        self.user.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        res = self.app.get(
            url,
            auth=user2.auth,
        )
        nt.assert_equal(res.json.get('twitter'), 'howtopizza')
        nt.assert_equal(res.json.get('profileWebsites'), ['http://www.cos.io'])
        nt.assert_true(res.json.get('github') is None)
        nt.assert_false(res.json['editable'])
        nt.assert_equal(res.json.get('erad'), '123')

    def test_serialize_social_with_erad_and_editable(self):
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io',
                                               'http://www.osf.io',
                                               'http://www.wordup.com']
        self.user.erad = '123'
        self.user.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        print(res)
        nt.assert_equal(res.json.get('twitter'), 'howtopizza')
        nt.assert_equal(res.json.get('profileWebsites'),
                        [
                            'http://www.cos.io',
                            'http://www.osf.io',
                            'http://www.wordup.com'
                        ])
        nt.assert_equal(res.json.get('erad'), '123')
        nt.assert_true(res.json.get('github') is None)
        nt.assert_true(res.json['editable'])

    def test_unserialize_names(self):
        fake_fullname_w_spaces = '    {}    '.format(fake.name())
        names = {
            'full': fake_fullname_w_spaces,
            'given': 'Tea',
            'middle': 'Gray',
            'family': 'Pot',
            'suffix': 'Ms.',
            'given_en': 'Tony',
            'middle_en': 'lil',
            'family_en': 'Micheal',
        }

        url = api_url_for('unserialize_names')
        res = self.app.put_json(url, names, auth=self.user.auth)
        nt.assert_equal(res.status_code, 200)
        self.user.reload()

        nt.assert_equal(self.user.fullname, fake_fullname_w_spaces.strip())
        nt.assert_equal(self.user.given_name, names['given'])
        nt.assert_equal(self.user.middle_names, names['middle'])
        nt.assert_equal(self.user.family_name, names['family'])
        nt.assert_equal(self.user.suffix, names['suffix'])
        nt.assert_equal(self.user.given_name_en, names['given_en'])
        nt.assert_equal(self.user.middle_names_en, names['middle_en'])
        nt.assert_equal(self.user.family_name_en, names['family_en'])

    def test_serialize_account_info(self):
        url = api_url_for('serialize_account_info')

        response = self.app.get(
            url,
            auth=self.user.auth,
        )

        nt.assert_equal(response.status_code, 200)
        response_data = response.body
        response_data = json.loads(response_data)
        nt.assert_equal(response_data['full'], self.user.fullname)
        nt.assert_equal(response_data['given'], self.user.given_name)
        nt.assert_equal(response_data['middle'], self.user.middle_names)
        nt.assert_equal(response_data['family'], self.user.family_name)
        nt.assert_equal(response_data['given_en'], self.user.given_name_en)
        nt.assert_equal(response_data['middle_en'], self.user.middle_names_en)
        nt.assert_equal(response_data['family_en'], self.user.family_name_en)
        nt.assert_equal(response_data['suffix'], self.user.suffix)
        nt.assert_equal(response_data['erad'], self.user.erad)
        nt.assert_equal(response_data['institution'], None)
        nt.assert_equal(response_data['department'], None)
        nt.assert_equal(response_data['institution_en'], None)
        nt.assert_equal(response_data['department_en'], None)

    def test_unserialize_account_info_without_jobs(self):
        url = api_url_for('serialize_account_info')
        payload = {
            'full': self.user.fullname,
            'given': self.user.given_name,
            'middle': self.user.middle_names,
            'family': self.user.family_name,
            'given_en': self.user.given_name_en,
            'middle_en': self.user.middle_names_en,
            'family_en': self.user.family_name_en,
            'suffix': self.user.suffix,
            'erad': self.user.erad,
            'institution': None,
            'department': None,
            'institution_en': None,
            'department_en': None,
        }

        self.app.put_json(
            url,
            payload,
            auth=self.user.auth
        )

        self.user.reload()

        nt.assert_equal(self.user.fullname, payload['full'])
        nt.assert_equal(self.user.given_name, payload['given'])
        nt.assert_equal(self.user.middle_names, payload['middle'])
        nt.assert_equal(self.user.family_name, payload['family'])
        nt.assert_equal(self.user.given_name_en, payload['given_en'])
        nt.assert_equal(self.user.middle_names_en, payload['middle_en'])
        nt.assert_equal(self.user.family_name_en, payload['family_en'])
        nt.assert_equal(self.user.suffix, payload['suffix'])
        nt.assert_equal(self.user.erad, payload['erad'])
        nt.assert_equal(None, payload['institution'])
        nt.assert_equal(None, payload['department'])
        nt.assert_equal(None, payload['institution_en'])
        nt.assert_equal(None, payload['department_en'])

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_unserialize_account_info_with_jobs(self, mock_check_spam):
        url = api_url_for('serialize_account_info')
        jobs = [{
            'institution': 'an institution',
            'institution_en': 'Institution',
            'department': 'department A',
            'department_en': 'Department A',
            'location': 'Anywhere',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }, {
            'institution': 'another institution',
            'institution_en': 'Another Institution',
            'department': 'department B',
            'department_en': 'Department B',
            'location': 'Nowhere',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }]
        self.user.jobs = jobs
        self.user.save()

        payload = {
            'full': self.user.fullname,
            'given': self.user.given_name,
            'middle': self.user.middle_names,
            'family': self.user.family_name,
            'given_en': self.user.given_name_en,
            'middle_en': self.user.middle_names_en,
            'family_en': self.user.family_name_en,
            'suffix': self.user.suffix,
            'erad': self.user.erad,
            'institution': 'change institution',
            'department': 'change department',
            'institution_en': 'Change Institution',
            'department_en': 'Change Department',
        }

        self.app.put_json(
            url,
            payload,
            auth=self.user.auth
        )

        self.user.reload()

        nt.assert_equal(
            self.user.jobs[0]['institution'], payload['institution'])
        nt.assert_equal(
            self.user.jobs[0]['department'], payload['department'])
        nt.assert_equal(
            self.user.jobs[0]['institution_en'], payload['institution_en'])
        nt.assert_equal(
            self.user.jobs[0]['department_en'], payload['department_en'])

        assert mock_check_spam.called

    def test_serialize_name(self):
        url = api_url_for('serialize_names')
        response = self.app.get(
            url,
            auth=self.user.auth,
        )

        nt.assert_equal(response.status_code, 200)
        response_data = response.body
        response_data = json.loads(response_data)

        nt.assert_equal(response_data['full'], self.user.fullname)
        nt.assert_equal(response_data['given'], self.user.given_name)
        nt.assert_equal(response_data['middle'], self.user.middle_names)
        nt.assert_equal(response_data['family'], self.user.family_name)
        nt.assert_equal(response_data['given_en'], self.user.given_name_en)
        nt.assert_equal(response_data['middle_en'], self.user.middle_names_en)
        nt.assert_equal(response_data['family_en'], self.user.family_name_en)
        nt.assert_equal(response_data['suffix'], self.user.suffix)

    def test_unserialize_social(self):
        erad = '007'
        url = api_url_for('unserialize_social')
        payload = {
            'profileWebsites': ['http://frozen.pizza.com/reviews'],
            'twitter': 'howtopizza',
            'github': 'frozenpizzacode',
            'erad': erad
        }

        self.app.put_json(
            url,
            payload,
            auth=self.user.auth,
        )
        self.user.reload()

        self.user.social['profileWebsites'] = payload['profileWebsites']
        self.user.social['twitter'] = payload['twitter']
        self.user.social['github'] = payload['github']
        self.user.erad = payload['erad']

        nt.assert_true(self.user.social['researcherId'] is None)

    def test_append_idp_attr_common(self):
        ext, created = UserExtendedData.objects.get_or_create(user=self.user)
        # update every login.
        ext.set_idp_attr(
            {
                'idp': 'identify provider',
                'eppn': 'eppn@mail.com',
                'fullname': 'fullname',
                'fullname_ja': 'fullname ja',
                'entitlement': 'Entitlement',
                'email': 'abc@mail.com',
                'organization_name': 'a organization',
                'organizational_unit': 'a organizational unit',
                'organization_name_en': 'a organization en',
                'organizational_unit_en': 'a organizational unit en',
            },
        )

        data = {
            'idp_attr': ''
        }

        self.user.save()

        append_idp_attr_common(data, self.user)

        nt.assert_equal(data['idp_attr']['institution'],
                        self.user.ext.data['idp_attr']['organization_name'])
        nt.assert_equal(data['idp_attr']['department'],
                        self.user.ext.data['idp_attr']['organizational_unit'])
        nt.assert_equal(data['idp_attr']['institution_en'],
                        self.user.ext.data['idp_attr']['organization_name_en'])
        nt.assert_equal(
            data['idp_attr']['department_en'],
            self.user.ext.data['idp_attr']
            ['organizational_unit_en'])

    def test_serialize_job(self):
        job = {
            'institution': 'an institution',
            'institution_en': 'Institution',
            'department': 'department A',
            'department_en': 'Department A',
            'title': 'Title B',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }
        result = website_view.serialize_job(job)
        for key, value in job.items():
            nt.assert_equal(result[key], job[key])

    def test_serialize_school(self):
        school = {
            'institution': 'an institution',
            'department': 'a department',
            'institution_en': 'an institution en',
            'department_en': 'a department en',
            'degree': None,
            'startMonth': 1,
            'startYear': '2001',
            'endMonth': 5,
            'endYear': '2001',
            'ongoing': False,
        }
        result = website_view.serialize_school(school)
        for key, value in school.items():
            nt.assert_equal(result[key], school[key])

    def test_unserialize_job(self):
        job = {
            'institution': 'an institution',
            'department': 'a department',
            'institution_en': 'an institution en',
            'department_en': 'a department en',
            'title': 'a title',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }
        result = website_view.unserialize_job(job)
        for key, value in job.items():
            nt.assert_equal(result[key], job[key])

    def test_unserialize_school(self):
        school = {
            'institution': 'an institution',
            'department': 'a department',
            'institution_en': 'an institution en',
            'department_en': 'a department en',
            'degree': None,
            'startMonth': 1,
            'startYear': '2001',
            'endMonth': 5,
            'endYear': '2001',
            'ongoing': False,
        }
        result = website_view.unserialize_school(school)
        for key, value in school.items():
            nt.assert_equal(result[key], school[key])
