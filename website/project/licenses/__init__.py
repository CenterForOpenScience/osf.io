from django.apps import apps
from rest_framework.exceptions import ValidationError

from framework import exceptions as framework_exceptions
from osf import exceptions as osf_exceptions
from osf.utils import permissions


def set_license(node, license_detail, auth, node_type='node'):
    NodeLicense = apps.get_model('osf.NodeLicense')
    NodeLicenseRecord = apps.get_model('osf.NodeLicenseRecord')

    if node_type not in ['node', 'preprint']:
        raise ValueError(f'{node_type} is not a valid node_type argument')

    license_record = node.node_license if node_type == 'node' else node.license

    license_id = license_detail.get('id')
    license_year = license_detail.get('year')
    copyright_holders = license_detail.get('copyrightHolders', [])

    if license_record and (
        license_id == license_record.license_id and
        license_year == license_record.year and
        sorted(copyright_holders) == sorted(license_record.copyright_holders)
    ):
        return {}, False

    if not node.has_permission(auth.user, permissions.WRITE):
        raise framework_exceptions.PermissionsError(f'You need admin or write permissions to change a {node_type}\'s license')

    try:
        node_license = NodeLicense.objects.get(license_id=license_id)
    except NodeLicense.DoesNotExist:
        raise osf_exceptions.NodeStateError(f'Trying to update a {node_type} with an invalid license')

    if node_type == 'preprint':
        if node.provider.licenses_acceptable.exists() and not node.provider.licenses_acceptable.filter(id=node_license.id):
            raise framework_exceptions.PermissionsError(f'Invalid license chosen for {node.provider.name}')

    for required_property in node_license.properties:
        if not license_detail.get(required_property):
            raise ValidationError(f'{required_property} must be specified for this license')

    if license_record is None:
        license_record = NodeLicenseRecord(node_license=node_license)
    license_record.node_license = node_license
    license_record.year = license_year
    license_record.copyright_holders = copyright_holders
    license_record.save()
    if node_type == 'node':
        node.node_license = license_record
    elif node_type == 'preprint':
        node.license = license_record

    return license_record, True
