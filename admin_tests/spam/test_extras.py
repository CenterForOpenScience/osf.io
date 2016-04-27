from nose import tools as nt
from django.test import SimpleTestCase

from admin.spam.templatetags import spam_extras


class TestReverseTags(SimpleTestCase):
    def test_reverse_spam_detail(self):
        res = spam_extras.reverse_spam_detail('123ab', page='2', status='4')
        nt.assert_in('/admin/spam/123ab/?', res)
        nt.assert_in('page=2', res)
        nt.assert_in('status=4', res)
        nt.assert_equal(len('/admin/spam/123ab/?page=2&status=4'), len(res))

    def test_reverse_spam_list(self):
        res = spam_extras.reverse_spam_list(page='2', status='4')
        nt.assert_in('/admin/spam/?', res)
        nt.assert_in('page=2', res)
        nt.assert_in('status=4', res)
        nt.assert_equal(len('/admin/spam/?page=2&status=4'), len(res))

    def test_reverse_spam_user(self):
        res = spam_extras.reverse_spam_user('kzzab', page='2', status='4')
        nt.assert_in('/admin/spam/user/kzzab/?', res)
        nt.assert_in('page=2', res)
        nt.assert_in('status=4', res)
        nt.assert_equal(len('/admin/spam/user/kzzab/?page=2&status=4'),
                        len(res))

    def test_reverse_spam_email(self):
        res = spam_extras.reverse_spam_email('123ab', page='2', status='4')
        nt.assert_in('/admin/spam/123ab/email/?', res)
        nt.assert_in('page=2', res)
        nt.assert_in('status=4', res)
        nt.assert_equal(len('/admin/spam/123ab/email/?page=2&status=4'),
                        len(res))
