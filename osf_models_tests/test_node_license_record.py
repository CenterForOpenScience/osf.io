import pytest

from .factories import NodeLicenseRecordFactory

@pytest.mark.django_db
def test_factory():
    nlr = NodeLicenseRecordFactory()
    assert nlr.node_license
    assert nlr.node_license.name
    assert nlr.node_license.license_id
    assert nlr.year
    assert nlr.copyright_holders

@pytest.mark.django_db
class TestNodeLicenseRecord:

    def test_copy(self):
        nlr = NodeLicenseRecordFactory()
        copy = nlr.copy()
        assert copy.node_license == nlr.node_license
        assert copy.year == nlr.year
        assert copy.copyright_holders == nlr.copyright_holders
