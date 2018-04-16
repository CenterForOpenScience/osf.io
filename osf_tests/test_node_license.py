import pytest

from osf.models import NodeLicense

pytestmark = pytest.mark.django_db

def test_manager_methods():
    # Projects can't have CCBYNCND but preprints can
    assert 'CCBYNCND' not in list(NodeLicense.objects.project_licenses().values_list('license_id', flat=True))
    assert 'CCBYNCND' in list(NodeLicense.objects.preprint_licenses().values_list('license_id', flat=True))
