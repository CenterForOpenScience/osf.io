import json
import os
import warnings

from django.apps import apps
from modularodm import Q
from osf.exceptions import ValidationError
from modularodm import exceptions as modm_exceptions

from framework import exceptions as framework_exceptions

from website import exceptions as web_exceptions
from website import settings
from website.util import permissions


def ensure_licenses(warn=True):
    """Upsert the licenses in our database based on a JSON file.

    :return tuple: (number inserted, number updated)

    """
    NodeLicense = apps.get_model('osf.NodeLicense')
    ninserted = 0
    nupdated = 0
    with open(
            os.path.join(
                settings.APP_PATH,
                'node_modules', 'list-of-licenses', 'dist', 'list-of-licenses.json'
            )
    ) as fp:
        licenses = json.loads(fp.read())
        for id, info in licenses.items():
            name = info['name']
            text = info['text']
            properties = info.get('properties', [])
            try:

                model_kwargs = dict(
                    license_id=id,
                    name=name,
                    text=text,
                    properties=properties
                )
                if not settings.USE_POSTGRES:
                    del model_kwargs['license_id']
                    model_kwargs['id'] = id
                NodeLicense(**model_kwargs).save()
            except (modm_exceptions.KeyExistsException, ValidationError):
                license_id_field = 'license_id' if settings.USE_POSTGRES else 'id'
                node_license = NodeLicense.find_one(
                    Q(license_id_field, 'eq', id)
                )
                node_license.name = name
                node_license.text = text
                node_license.properties = properties
                node_license.save()
                nupdated += 1
            else:
                if warn:
                    warnings.warn(
                        'License {name} ({id}) added to the database.'.format(
                            name=name,
                            id=id
                        )
                    )
                ninserted += 1
    return ninserted, nupdated


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

    if not node.has_permission(auth.user, permissions.ADMIN):
        raise framework_exceptions.PermissionsError('Only admins can change a {}\'s license'.format(node_type))

    try:
        node_license = NodeLicense.find_one(
            Q('license_id', 'eq', license_id)
        )
    except modm_exceptions.NoResultsFound:
        raise web_exceptions.NodeStateError('Trying to update a {} with an invalid license'.format(node_type))

    if node_type == 'preprint':
        if node.provider.licenses_acceptable.exists() and not node.provider.licenses_acceptable.filter(id=node_license.id):
            raise framework_exceptions.PermissionsError('Invalid license chosen for {}'.format(node.provider.name))

    for required_property in node_license.properties:
        if not license_detail.get(required_property):
            raise modm_exceptions.ValidationValueError('{} must be specified for this license'.format(required_property))

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
