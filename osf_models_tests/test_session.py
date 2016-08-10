import pytest

from osf_models.models import Session

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
