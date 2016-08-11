import pytest

from osf_models.models import Guid
from .factories import UserFactory, NodeFactory

@pytest.mark.django_db
class TestReferent:

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory
    ])
    def test_referent(self, Factory):
        obj = Factory()
        guid = Guid.objects.get(guid=obj._id)
        assert guid.referent == obj

    def test_referent_can_be_set(self):
        user = UserFactory()
        node = NodeFactory()

        guid = Guid.load(user._id)
        assert guid.referent == user  # sanity check

        node._guid = None
        node.save()
        guid.referent = node

        # Guid points to both node and user
        assert node._id == guid.guid
        assert user._id == guid.guid
