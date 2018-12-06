from django.apps import apps
from django.core.exceptions import ValidationError

from framework import exceptions as framework_exceptions
from website import exceptions as web_exceptions
from osf.utils import permissions


def set_license(node, license_detail, auth, node_type='node'):
    NodeLicense = apps.get_model('osf.NodeLicense')
    NodeLicenseRecord = apps.get_model('osf.NodeLicenseRecord')

    if node_type not in ['node', 'preprint']:
        raise ValueError('{} is not a valid node_type argument'.format(node_type))

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

    if node_type == 'preprint':
        if not node.has_permission(auth.user, permissions.WRITE):
            raise framework_exceptions.PermissionsError('You need admin or write permissions to change a {}\'s license'.format(node_type))
    else:
        if not node.has_permission(auth.user, permissions.ADMIN):
            raise framework_exceptions.PermissionsError('Only admins can change a {}\'s license'.format(node_type))

    try:
        node_license = NodeLicense.objects.get(license_id=license_id)
    except NodeLicense.DoesNotExist:
        raise web_exceptions.NodeStateError('Trying to update a {} with an invalid license'.format(node_type))

    if node_type == 'preprint':
        if node.provider.licenses_acceptable.exists() and not node.provider.licenses_acceptable.filter(id=node_license.id):
            raise framework_exceptions.PermissionsError('Invalid license chosen for {}'.format(node.provider.name))

    for required_property in node_license.properties:
        if not license_detail.get(required_property):
            raise ValidationError('{} must be specified for this license'.format(required_property))

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
