import pytest

from osf.models import Session
from osf.modm_compat import Q

@pytest.mark.django_db
class TestSession:

    def test_is_authenticated(self):
        session = Session(data={'auth_user_id': 'abc12'})
        assert session.is_authenticated

        session2 = Session()
        assert session2.is_authenticated is False

    def test_loading_by_id(self):
        session = Session()
        session.save()

        assert Session.load(session._id)

    def test_remove(self):
        session, session2 = Session(data={'auth_user_id': '123ab'}), Session(data={'auth_user_id': 'ab123'})
        session.save()
        session2.save()

        assert Session.objects.count() == 2  # sanity check
        Session.remove(Q('data.auth_user_id', 'eq', '123ab'))
        assert Session.objects.count() == 1
