import pytest

from osf_models.models import Guid, NodeLicenseRecord, OSFUser
from osf_models.modm_compat import Q
from .factories import UserFactory, NodeFactory, NodeLicenseRecordFactory, RegistrationFactory

@pytest.mark.django_db
class TestGuid:

    def test_long_id_gets_generated_on_creation(self):
        obj = NodeLicenseRecordFactory()
        assert obj._id
        assert len(obj._id) > 5

    def test_loading_by_object_id(self):
        obj = NodeLicenseRecordFactory()
        assert NodeLicenseRecord.load(obj._id) == obj

    def test_loading_by_short_guid(self):
        obj = UserFactory()
        assert OSFUser.load(obj._id) == obj

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory,
        RegistrationFactory,
    ])
    def test_short_guid_gets_generated_on_creation(self, Factory):
        obj = Factory()
        assert obj._id
        assert len(obj._id) == 5

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

    def test_querying_on_referent(self):
        user = UserFactory()

        guids = Guid.find(Q('referent', 'eq', user))
        assert user.guid in guids

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

        user_guid = user.guid
        node_guid = node.guid

        user.guid = node_guid
        node.guid = user_guid

        assert node_guid == user.guid
        assert user_guid == node.guid

    def test_id_matches(self):
        user = UserFactory()

        assert user._id == user.guid.guid

    @pytest.mark.parametrize('Factory',
     [
         UserFactory,
         NodeFactory
     ])
    def test_nulling_out_guid(self, Factory):
        obj = Factory()

        guid = Guid.load(obj._id)

        obj.guid = None

        obj.save()
        obj.refresh_from_db()

        # queryset cache returns the old version
        guid.refresh_from_db()

        assert obj.guid != guid

        assert guid.guid != obj.guid.guid
