# -*- coding: utf-8 -*-
from nose import tools as nt

from tests.base import AdminTestCase
from admin.rdm_announcement.forms import PreviewForm
from random import Random

data = dict(
    title ='test title',
    body ='test body',
    announcement_type='Email',
)

class TestPreviewForm(AdminTestCase):

    def test_clean_from_email_okay(self):
        mod_data = dict(data)
        email_body = self.random_body(10000)
        mod_data.update({'body': email_body,})
        form = PreviewForm(data=mod_data)
        self.assertTrue(form.is_valid())

    def test_clean_from_twitter_okay(self):
        mod_data = dict(data)
        twitter_body = self.random_body(140)
        mod_data.update({'body': twitter_body,'announcement_type':'SNS (Twitter)'})
        form = PreviewForm(data=mod_data)
        self.assertTrue(form.is_valid())

    def test_clean_from_twitter_raise(self):
        mod_data = dict(data)
        twitter_body = self.random_body(141)
        mod_data.update({'body': twitter_body,'announcement_type':'SNS (Twitter)'})
        form = PreviewForm(data=mod_data)
        nt.assert_false(form.is_valid())
        nt.assert_in('Body should be at most 140 characters', form.errors['__all__'])

    def test_clean_from_push_okay(self):
        mod_data = dict(data)
        twitter_body = self.random_body(2000)
        mod_data.update({'body': twitter_body,'announcement_type':'Push notification'})
        form = PreviewForm(data=mod_data)
        self.assertTrue(form.is_valid())

    def test_clean_from_push_raise(self):
        mod_data = dict(data)
        push_body = self.random_body(2001)
        mod_data.update({'body': push_body,'announcement_type':'Push notification'})
        form = PreviewForm(data=mod_data)
        nt.assert_false(form.is_valid())
        nt.assert_in('Body should be at most 2000 characters', form.errors['__all__'])

    def test_clean_from_facebook_okay(self):
        mod_data = dict(data)
        facebook_body = self.random_body(10000)
        mod_data.update({'body': facebook_body,'announcement_type':'SNS (Facebook)'})
        form = PreviewForm(data=mod_data)
        self.assertTrue(form.is_valid())

    def random_body(self,count):
        body = ''
        chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789-_'
        length = len(chars) - 1
        random = Random()
        for i in range(0, count):
            body += chars[random.randint(0, length)]
        return body
