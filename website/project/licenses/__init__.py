import functools
import json
import os
import warnings

from modularodm import fields, Q
from modularodm.exceptions import KeyExistsException

from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)

from website import settings


def _serialize(fields, instance):
    return {
        field: getattr(instance, field)
        for field in fields
    }

serialize_node_license = functools.partial(_serialize, ('id', 'name', 'text'))


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
                    id=id,
                    name=name,
                    text=text,
                    properties=properties
                ).save()
            except KeyExistsException:
                node_license = NodeLicense.find_one(
                    Q('id', 'eq', id)
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
