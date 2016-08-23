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

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory
    ])
    def test_referent_can_be_set(self, Factory):
        obj = Factory()
        obj1 = Factory()

        guid = Guid.load(obj._id)
        assert guid.referent == obj  # sanity check

        guid.referent = obj1
        assert guid.referent == obj1

    def test_swapping_guids(self):
        user = UserFactory()
        node = NodeFactory()

        user_guid = user._guid
        node_guid = node._guid

        user._guid = node_guid
        node._guid = user_guid

        assert node_guid == user._guid
        assert user_guid == node._guid

    def test_id_matches(self):
        user = UserFactory()

        assert user._id == user._guid.guid

    @pytest.mark.parametrize('Factory',
     [
         UserFactory,
         NodeFactory
     ])
    def test_nulling_out_guid(self, Factory):
        obj = Factory()

        guid = Guid.load(obj._id)

        obj._guid = None

        obj.save()
        obj.refresh_from_db()

        # queryset cache returns the old version
        guid.refresh_from_db()

        assert obj._guid != guid

        assert guid.guid != obj._guid.guid
