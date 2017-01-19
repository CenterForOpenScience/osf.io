import json
import os
import warnings

from modularodm import fields, Q
from osf.exceptions import ValidationError
from modularodm import exceptions as modm_exceptions

from framework import exceptions as framework_exceptions
from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)

from website import exceptions as web_exceptions
from website import settings
from website.util import permissions


def _serialize(fields, instance):
    return {
        field: getattr(instance, field)
        for field in fields
    }

def serialize_node_license(node_license):
    return {
        'id': node_license.license_id,
        'name': node_license.name,
        'text': node_license.text,
    }

def serialize_node_license_record(node_license_record):
    if node_license_record is None:
        return {}
    ret = serialize_node_license(node_license_record.node_license)
    ret.update(_serialize(('year', 'copyright_holders'), node_license_record))
    return ret


@mongo_utils.unique_on(['id'])
@mongo_utils.unique_on(['name'])
class NodeLicense(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    id = fields.StringField(
        required=True,
        unique=False,   # Skip modular-odm's uniqueness implementation, depending on MongoDB's
                        # instead (the decorator will install the proper index), so that we can
                        # kludge a non-racey upsert in ensure_licenses.
        editable=False
    )
    name = fields.StringField(
        required=True,
        unique=False    # Ditto.
    )
    text = fields.StringField(required=True)
    properties = fields.StringField(list=True)


class NodeLicenseRecord(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    node_license = fields.ForeignField('nodelicense', required=True)
    # Deliberately left as a StringField to support year ranges (e.g. 2012-2015)
    year = fields.StringField()
    copyright_holders = fields.StringField(list=True)

    @property
    def name(self):
        return self.node_license.name if self.node_license else None

    @property
    def text(self):
        return self.node_license.text if self.node_license else None

    @property
    def id(self):
        return self.node_license.id if self.node_license else None

    def to_json(self):
        return serialize_node_license_record(self)

    def copy(self):
        copied = NodeLicenseRecord(
            node_license=self.node_license,
            year=self.year,
            copyright_holders=self.copyright_holders
        )
        copied.save()
        return copied


def ensure_licenses(warn=True):
    """Upsert the licenses in our database based on a JSON file.

    :return tuple: (number inserted, number updated)

    """
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
                NodeLicense(
                    license_id=id,
                    name=name,
                    text=text,
                    properties=properties
                ).save()
            except (modm_exceptions.KeyExistsException, ValidationError):
                node_license = NodeLicense.find_one(
                    Q('license_id', 'eq', id)
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
