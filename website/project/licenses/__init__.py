import functools
import json
import os
import warnings

from modularodm import fields, Q
from modularodm.exceptions import NoResultsFound

from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)

from website import settings


@mongo_utils.unique_on(['id', 'name', '_id'])
class NodeLicense(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    id = fields.StringField(required=True, unique=True, editable=False)
    name = fields.StringField(required=True, unique=True, editable=False)
    text = fields.StringField(required=True, editable=False)
    properties = fields.StringField(list=True, editable=False)

class NodeLicenseRecord(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    node_license = fields.ForeignField('nodelicense', required=True)
    # Deliberately left as a StringField to support year ranges (e.g. 2012-2015)
    year = fields.StringField()
    copyright_holders = fields.StringField(list=True)

    def copy(self):
        copied = NodeLicenseRecord(
            node_license=self.node_license,
            year=self.year,
            copyright_holders=self.copyright_holders
        )
        copied.save()
        return copied

def _serialize(fields, instance):
    return {
        field: getattr(instance, field)
        for field in fields
    }

serialize_node_license = functools.partial(_serialize, ('id', 'name', 'text'))

def serialize_node_license_record(node_license_record):
    ret = serialize_node_license(node_license_record.node_license)
    ret.update(_serialize(node_license_record, ('year', 'copyright_holders')))

model = NodeLicense
serializer = serialize_node_license_record


def ensure_licenses():
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
                NodeLicense.find_one(
                    Q('name', 'eq', name) &
                    Q('id', 'eq', id)
                )
            except NoResultsFound:
                warnings.warn(
                    "License {name} ({id}) not already in the database. Adding it now.".format(
                        name=name,
                        id=id
                    )
                )
                node_license = NodeLicense(
                    id=id,
                    name=name,
                    text=text,
                    properties=properties
                )
                node_license.save()
