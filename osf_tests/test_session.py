import pytest

from framework.sessions import utils
from tests.base import DbTestCase
from osf_tests.factories import UserFactory
from osf.models import OSFUser

# @pytest.mark.django_db
# class TestSession:

#     def test_is_authenticated(self):
#         session = Session(data={'auth_user_id': 'abc12'})
#         assert session.is_authenticated

#         session2 = Session()
#         assert session2.is_authenticated is False

#     def test_loading_by_id(self):
#         session = Session()
#         session.save()

#         assert Session.load(session._id)

#     def test_remove(self):
#         session, session2 = Session(data={'auth_user_id': '123ab'}), Session(data={'auth_user_id': 'ab123'})
#         session.save()
#         session2.save()

#         assert Session.objects.count() == 2  # sanity check
#         Session.objects.filter(data__auth_user_id='123ab').delete()
#         assert Session.objects.count() == 1


# class SessionUtilsTestCase(DbTestCase):
    # def setUp(self, *args, **kwargs):
    #     super(SessionUtilsTestCase, self).setUp(*args, **kwargs)
    #     self.user = UserFactory()
    #     # Ensure usable password
    #     self.user.set_password('usablepassword')

    # def tearDown(self, *args, **kwargs):
    #     super(SessionUtilsTestCase, self).tearDown(*args, **kwargs)
    #     OSFUser.objects.all().delete()
    #     Session.objects.all().delete()

    # def test_remove_session_for_user(self):
    #     SessionFactory(user=self.user)

    #     # sanity check
    #     assert Session.objects.all().count() == 1

    #     utils.remove_sessions_for_user(self.user)
    #     assert Session.objects.all().count() == 0

    #     SessionFactory()
    #     SessionFactory(user=self.user)

    #     # sanity check
    #     assert Session.objects.all().count() == 2

    #     utils.remove_sessions_for_user(self.user)
    #     assert Session.objects.all().count() == 1

    # def test_password_change_clears_sessions(self):
    #     SessionFactory(user=self.user)
    #     SessionFactory(user=self.user)
    #     SessionFactory(user=self.user)
    #     assert Session.objects.all().count() == 3
    #     self.user.set_password('killerqueen')
    #     assert Session.objects.all().count() == 0

    # def test_remove_session(self):
    #     session = SessionFactory(user=self.user)
    #     assert Session.objects.all().count() == 1
    #     utils.remove_session(session)
    #     assert Session.objects.all().count() == 0
