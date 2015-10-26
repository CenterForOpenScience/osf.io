from nose.tools import *  # flake8: noqa

from website.util import permissions

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase

from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    AlternativeCitationFactory
)

class TestCreateAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestCreateAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()

        self.public = ProjectFactory(creator=self.user, is_public=True)
        self.private = ProjectFactory(creator=self.user, is_public=False)
        self.citation = AlternativeCitationFactory(name="name", text="text")
        self.public.alternativeCitations.append(self.citation)
        self.private.alternativeCitations.append(self.citation)
        self.public.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.private.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.public.save()
        self.private.save()
        self.public_url = '/{}nodes/{}/citations/'.format(API_BASE, self.public._id)
        self.private_url = '/{}nodes/{}/citations/'.format(API_BASE, self.private._id)
        self.citation.public_url = self.public_url + '{}/'.format(self.citation._id)
        self.citation.private_url = self.private_url + '{}/'.format(self.citation._id)

    def payload(self, name=None, text=None, id=None):
        payload = {'data': {
            'type': 'citations',
            'attributes': {
                'name': name,
                'text': text
                }
            }
        }
        if id is not None:
            payload['data']['id'] = id
        return payload

    def test_add_citation_admin(self):
        res = self.app.post_json_api(self.public_url, self.payload(name='Test', text='Citation'), auth=self.user.auth)
        assert_equal(res.status_code, 201)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 2)

        res = self.app.post_json_api(self.private_url, self.payload(name='Test', text='Citation'), auth=self.user.auth)
        assert_equal(res.status_code, 201)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 2)

    def test_add_citation_non_admin(self):
        res = self.app.post_json_api(self.public_url, self.payload(name='Test', text='Citation'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='Test', text='Citation'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

        res = self.app.post_json_api(self.public_url, self.payload(name='Test', text='Citation'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='Test', text='Citation'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

    def test_add_repeat_name_admin(self):
        res = self.app.post_json_api(self.public_url, self.payload(name='name', text='Citation'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name'")
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='name', text='Citation'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name'")
        assert_equal(len(self.private.alternativeCitations), 1)

    def test_add_repeat_name_non_admin(self):
        res = self.app.post_json_api(self.public_url, self.payload(name='name', text='Citation'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='name', text='Citation'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

        res = self.app.post_json_api(self.public_url, self.payload(name='name', text='Citation'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='name', text='Citation'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

    def test_add_repeat_text_admin(self):
        res = self.app.post_json_api(self.public_url, self.payload(name='Citation', text='text'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name'")
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='Citation', text='text'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name'")
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

    def test_add_repeat_text_non_admin(self):
        res = self.app.post_json_api(self.public_url, self.payload(name='Citation', text='text'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='Citation', text='text'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

        res = self.app.post_json_api(self.public_url, self.payload(name='Citation', text='text'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='Citation', text='text'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

    def test_add_repeat_name_and_text_admin(self):
        res = self.app.post_json_api(self.public_url, self.payload(name='name', text='text'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name'")
        assert_equal(res.json['errors'][1]['detail'], "Citation matches 'name'")
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='name', text='text'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name'")
        assert_equal(res.json['errors'][1]['detail'], "Citation matches 'name'")
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

    def test_add_repeat_name_and_text_non_admin(self):
        res = self.app.post_json_api(self.public_url, self.payload(name='name', text='text'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='name', text='text'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

        res = self.app.post_json_api(self.public_url, self.payload(name='name', text='text'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.post_json_api(self.private_url, self.payload(name='name', text='text'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

class TestUpdateAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestUpdateAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()

        self.public = ProjectFactory(creator=self.user, is_public=True)
        self.private = ProjectFactory(creator=self.user, is_public=False)
        self.citation = AlternativeCitationFactory(name="name", text="text")
        self.citation2 = AlternativeCitationFactory(name="name2", text="text2")
        self.public.alternativeCitations.append(self.citation)
        self.private.alternativeCitations.append(self.citation)
        self.public.alternativeCitations.append(self.citation2)
        self.private.alternativeCitations.append(self.citation2)
        self.public.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.private.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.public.save()
        self.private.save()
        self.public_url = '/{}nodes/{}/citations/'.format(API_BASE, self.public._id)
        self.private_url = '/{}nodes/{}/citations/'.format(API_BASE, self.private._id)
        self.citation.public_url = self.public_url + '{}/'.format(self.citation._id)
        self.citation.private_url = self.private_url + '{}/'.format(self.citation._id)

    def payload(self, name=None, text=None, id=None):
        payload = {'data': {
            'type': 'citations',
            'attributes': {
                'name': name,
                'text': text
                }
            }
        }
        if id is not None:
            payload['data']['id'] = id
        return payload

    def test_update_citation_name_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="Test", text="text", id=self.citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.citation.reload()
        assert_equal(self.citation.name, "Test")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="Test", text="text", id=self.citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.citation.reload()
        assert_equal(self.citation.name, "Test")

    def test_update_citation_name_non_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="Test", text="text", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="Test", text="text", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="Test", text="text", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")
        res = self.app.put_json_api(self.citation.private_url, self.payload(name="Test", text="text", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")

    def test_update_citation_text_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name", text="Test", id=self.citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.citation.reload()
        assert_equal(self.citation.text, "Test")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name", text="Test", id=self.citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.citation.reload()
        assert_equal(self.citation.text, "Test")

    def test_update_citation_text_non_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name", text="Test", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name", text="Test", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name", text="Test", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name", text="Test", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")

    def test_update_citation_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="Test", text="Test", id=self.citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.citation.reload()
        assert_equal(self.citation.name, "Test")
        assert_equal(self.citation.text, "Test")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="Test", text="Test", id=self.citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.citation.reload()
        assert_equal(self.citation.name, "Test")
        assert_equal(self.citation.text, "Test")

    def test_update_citation_non_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="Test", text="Test", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")
        assert_equal(self.citation.text, "text")
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="Test", text="Test", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")
        assert_equal(self.citation.text, "text")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="Test", text="Test", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")
        assert_equal(self.citation.text, "text")
        res = self.app.put_json_api(self.citation.private_url, self.payload(name="Test", text="Test", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")
        assert_equal(self.citation.text, "text")

    def test_update_citation_repeat_name_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name2", text="Test", id=self.citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name2'")
        self.citation.reload()
        assert_equal(self.citation.name, "name")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name2", text="Test", id=self.citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name2'")
        self.citation.reload()
        assert_equal(self.citation.name, "name")

    def test_update_citation_repeat_name_non_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name2", text="Test", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name2", text="Test", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name2", text="Test", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")
        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name2", text="Test", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.name, "name")

    def test_update_citation_repeat_text_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name", text="text2", id=self.citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        self.citation.reload()
        assert_equal(self.citation.text, "text")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name", text="text2", id=self.citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        self.citation.reload()
        assert_equal(self.citation.text, "text")

    def test_update_citation_repeat_text_non_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name", text="text2", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name", text="text2", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name", text="text2", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name", text="text2", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")

    def test_update_citation_repeat_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name2", text="text2", id=self.citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name2'")
        assert_equal(res.json['errors'][1]['detail'], "Citation matches 'name2'")
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        assert_equal(self.citation.name, "name")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name2", text="text2", id=self.citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name2'")
        assert_equal(res.json['errors'][1]['detail'], "Citation matches 'name2'")
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        assert_equal(self.citation.name, "name")

    def test_update_citation_repeat_non_admin(self):
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name2", text="text2", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        assert_equal(self.citation.name, "name")
        res = self.app.put_json_api(self.citation.public_url, self.payload(name="name2", text="text2", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        assert_equal(self.citation.name, "name")

        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name2", text="text2", id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        assert_equal(self.citation.name, "name")
        res = self.app.put_json_api(self.citation.private_url, self.payload(name="name2", text="text2", id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.citation.reload()
        assert_equal(self.citation.text, "text")
        assert_equal(self.citation.name, "name")

class TestDeleteAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestDeleteAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()

        self.public = ProjectFactory(creator=self.user, is_public=True)
        self.private = ProjectFactory(creator=self.user, is_public=False)
        self.citation = AlternativeCitationFactory(name="name", text="text")
        self.public.alternativeCitations.append(self.citation)
        self.private.alternativeCitations.append(self.citation)
        self.public.save()
        self.private.save()
        self.public.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.private.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.public_url = '/{}nodes/{}/citations/'.format(API_BASE, self.public._id)
        self.private_url = '/{}nodes/{}/citations/'.format(API_BASE, self.private._id)
        self.public_url_bad = self.public_url + '1/'
        self.private_url_bad = self.private_url + '1/'
        self.citation.public_url = self.public_url + '{}/'.format(self.citation._id)
        self.citation.private_url = self.private_url + '{}/'.format(self.citation._id)

    def test_delete_citation_admin(self):
        res = self.app.delete_json_api(self.citation.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 204)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 0)

        res = self.app.delete_json_api(self.citation.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 204)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 0)

    def test_delete_citation_non_admin(self):
        res = self.app.delete_json_api(self.citation.public_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)
        res = self.app.delete_json_api(self.citation.public_url, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.delete_json_api(self.citation.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)
        res = self.app.delete_json_api(self.citation.private_url, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

    def test_delete_citation_admin_404(self):
        res = self.app.delete_json_api(self.public_url_bad, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.delete_json_api(self.private_url_bad, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

    def test_delete_citation_non_admin_404(self):
        res = self.app.delete_json_api(self.public_url_bad, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.delete_json_api(self.private_url_bad, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

        res = self.app.delete_json_api(self.public_url_bad, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public.reload()
        assert_equal(len(self.public.alternativeCitations), 1)

        res = self.app.delete_json_api(self.private_url_bad, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.private.reload()
        assert_equal(len(self.private.alternativeCitations), 1)

class TestGetAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestGetAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()

        self.public = ProjectFactory(creator=self.user, is_public=True)
        self.private = ProjectFactory(creator=self.user, is_public=False)
        self.citation = AlternativeCitationFactory(name="name", text="text")
        self.public.alternativeCitations.append(self.citation)
        self.private.alternativeCitations.append(self.citation)
        self.public.save()
        self.private.save()
        self.public.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.private.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.public_url = '/{}nodes/{}/citations/'.format(API_BASE, self.public._id)
        self.private_url = '/{}nodes/{}/citations/'.format(API_BASE, self.private._id)
        self.public_url_bad = self.public_url + '1/'
        self.private_url_bad = self.private_url + '1/'
        self.citation.public_url = self.public_url + '{}/'.format(self.citation._id)
        self.citation.private_url = self.private_url + '{}/'.format(self.citation._id)

    def test_get_citation_admin(self):
        res = self.app.get(self.citation.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

        res = self.app.get(self.citation.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_contrib_non_admin(self):
        res = self.app.get(self.citation.public_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

        res = self.app.get(self.citation.private_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_admin_404(self):
        res = self.app.get(self.public_url_bad, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        res = self.app.get(self.private_url_bad, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_citation_contrib_non_admin_404(self):
        res = self.app.get(self.public_url_bad, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        res = self.app.get(self.private_url_bad, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_citation_non_contrib_404(self):
        res = self.app.get(self.public_url_bad, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        res = self.app.get(self.private_url_bad, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_get_all_citations_admin(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_citations_contrib_non_admin(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

        res = self.app.get(self.private_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_citations_non_contrib(self):
        res = self.app.get(self.public_url, auth=self.user_three.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

        res = self.app.get(self.private_url, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

class TestRegistrationAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestRegistrationAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()

        self.public = ProjectFactory(creator=self.user, is_public=True)
        self.citation = AlternativeCitationFactory(name="name", text="text")
        self.public.alternativeCitations.append(self.citation)
        self.public.save()
        self.public.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)
        self.registration = RegistrationFactory(project=self.public)
        self.reg_url = '/{}nodes/{}/citations/'.format(API_BASE, self.registration._id)
        self.citation.reg_url = self.reg_url + '{}/'.format(self.citation._id)

    def payload(self, name=None, text=None, id=None):
        payload = {'data': {
            'type': 'citations',
            'attributes': {
                'name': name,
                'text': text
                }
            }
        }
        if id is not None:
            payload['data']['id'] = id
        return payload

    def test_get_all_reg_citations_admin(self):
        res = self.app.get(self.reg_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_reg_citations_contrib_non_admin(self):
        res = self.app.get(self.reg_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_reg_citations_non_contrib(self):
        res = self.app.get(self.reg_url, auth=self.user_three.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_reg_citation_admin(self):
        res = self.app.get(self.citation.reg_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_reg_citation_contrib_non_admin(self):
        res = self.app.get(self.citation.reg_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_reg_citation_non_contrib(self):
        res = self.app.get(self.citation.reg_url, auth=self.user_three.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_create_reg_citation_admin(self):
        res = self.app.post_json_api(self.reg_url, self.payload(name="test", text='Citation'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(self.registration.alternativeCitations), 1)

    def test_create_reg_citation_non_admin(self):
        res = self.app.post_json_api(self.reg_url, self.payload(name="test", text='Citation'), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(self.registration.alternativeCitations), 1)

        res = self.app.post_json_api(self.reg_url, self.payload(name="test", text='Citation'), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(self.registration.alternativeCitations), 1)

    def test_update_reg_citation_admin(self):
        res = self.app.put_json_api(self.citation.reg_url, self.payload(name="test", text='Citation', id=self.citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(self.citation.name, "name")
        assert_equal(self.citation.text, "text")

    def test_update_reg_citation_non_admin(self):
        res = self.app.put_json_api(self.citation.reg_url, self.payload(name="test", text='Citation', id=self.citation._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(self.citation.name, "name")
        assert_equal(self.citation.text, "text")

        res = self.app.put_json_api(self.citation.reg_url, self.payload(name="test", text='Citation', id=self.citation._id), auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(self.citation.name, "name")
        assert_equal(self.citation.text, "text")

    def test_delete_reg_citation_admin(self):
        res = self.app.delete(self.citation.reg_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(self.registration.alternativeCitations), 1)

    def test_delete_reg_citation_non_admin(self):
        res = self.app.delete(self.citation.reg_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(self.registration.alternativeCitations), 1)

        res = self.app.delete(self.citation.reg_url, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(self.registration.alternativeCitations), 1)
