import pytest

from nose import tools as nt

from admin.comments.templatetags import comment_extras


@pytest.mark.django_db
class TestReverseTags:
    @pytest.fixture(autouse=True)
    def override_urlconf(self, settings):
        settings.ROOT_URLCONF = 'admin.base.urls'

    def test_reverse_spam_detail(self):
        res = comment_extras.reverse_spam_detail('123ab', page='2', status='4')
        nt.assert_in('/spam/123ab/?', res)
        nt.assert_in('page=2', res)
        nt.assert_in('status=4', res)
        nt.assert_equal(len('/spam/123ab/?page=2&status=4'), len(res))

    def test_reverse_spam_list(self):
        res = comment_extras.reverse_spam_list(page='2', status='4')
        nt.assert_in('/spam/?', res)
        nt.assert_in('page=2', res)
        nt.assert_in('status=4', res)
        nt.assert_equal(len('/spam/?page=2&status=4'), len(res))

    def test_reverse_spam_user(self):
        res = comment_extras.reverse_spam_user('kzzab', page='2', status='4')
        nt.assert_in('/spam/user/kzzab/?', res)
        nt.assert_in('page=2', res)
        nt.assert_in('status=4', res)
        nt.assert_equal(len('/spam/user/kzzab/?page=2&status=4'),
                        len(res))
