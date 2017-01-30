# -*- coding: utf-8 -*-
import functools

from django.contrib.postgres.fields import ArrayField
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


def _serialize(fields, instance):
    return {
        field: getattr(instance, field)
        for field in fields
    }

serialize_node_license = functools.partial(_serialize, ('_id', 'name', 'text'))

def serialize_node_license_record(node_license_record):
    if node_license_record is None:
        return {}
    ret = serialize_node_license(node_license_record.node_license)
    ret.update(_serialize(('year', 'copyright_holders'), node_license_record))
    return ret


class NodeLicense(ObjectIDMixin, BaseModel):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.project.licenses.NodeLicense'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    license_id = models.CharField(max_length=128, null=False, unique=True)
    name = models.CharField(max_length=256, null=False, unique=True)
    text = models.TextField(null=False)
    properties = ArrayField(models.CharField(max_length=128), default=list, blank=True)

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        django_obj = super(NodeLicense, cls).migrate_from_modm(modm_obj)
        django_obj.license_id = django_obj.id
        django_obj.id = None
        return django_obj

    class Meta:
        unique_together = ['_id', 'license_id']


class NodeLicenseRecord(ObjectIDMixin, BaseModel):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.project.licenses.NodeLicenseRecord'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    node_license = models.ForeignKey('NodeLicense', null=True, blank=True, on_delete=models.SET_NULL)
    # Deliberately left as a CharField to support year ranges (e.g. 2012-2015)
    year = models.CharField(max_length=128, null=True, blank=True)
    copyright_holders = ArrayField(
        models.CharField(max_length=256, blank=True, null=True),
        default=list, blank=True)

    @property
    def name(self):
        return self.node_license.name if self.node_license else None

    @property
    def text(self):
        return self.node_license.text if self.node_license else None

    @property
    def license_id(self):
        return self.node_license.license_id if self.node_license else None

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

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        modm_obj.year = unicode(modm_obj.year)[:128]
        modm_obj.copyright_holders = [unicode(cph)[:256] for cph in modm_obj.copyright_holders]
        return super(NodeLicenseRecord, cls).migrate_from_modm(modm_obj)
