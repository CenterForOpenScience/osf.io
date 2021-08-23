# -*- coding: utf-8 -*-
import functools

from django.contrib.postgres.fields import ArrayField
from django.db import models
from osf.models.base import BaseModel, ObjectIDMixin


def _serialize(fields, instance):
    return {
        field: getattr(instance, field if field != 'id' else 'license_id')
        for field in fields
    }

serialize_node_license = functools.partial(_serialize, ('id', 'name', 'text'))

def serialize_node_license_record(node_license_record):
    if node_license_record is None:
        return {}
    ret = serialize_node_license(node_license_record.node_license)
    ret.update(_serialize(('year', 'copyright_holders'), node_license_record))
    return ret


class NodeLicenseManager(models.Manager):
    PREPRINT_ONLY_LICENSES = {
        'CCBYNCND',
        'CCBYSA40',
    }

    def preprint_licenses(self):
        return self.all()

    def project_licenses(self):
        return self.exclude(license_id__in=self.PREPRINT_ONLY_LICENSES)


class NodeLicense(ObjectIDMixin, BaseModel):
    license_id = models.CharField(
        max_length=128,
        null=False,
        unique=True,
        help_text='A unique id for the license. for example'
    )
    name = models.CharField(
        max_length=256,
        null=False,
        unique=True,
        help_text='The name of the license'
    )
    text = models.TextField(
        null=False,
        help_text='The text of the license with custom properties surround by curly brackets, for example: '
                  '<i>Copyright (c) {{year}}, {{copyrightHolders}} All rights reserved.</i>'
    )
    url = models.URLField(
        blank=True,
        help_text='The license\'s url for example: <i>http://opensource.org/licenses/BSD-3-Clause</i>'
    )
    properties = ArrayField(
        models.CharField(max_length=128),
        default=list,
        blank=True,
        help_text='The custom elements in a license\'s text surrounded with curly brackets for example: '
                  '<i>{year,copyrightHolders}</i>'
    )

    objects = NodeLicenseManager()

    def __str__(self):
        return f'{self.name} ({self.license_id})'

    class Meta:
        unique_together = ['_id', 'license_id']


class NodeLicenseRecord(ObjectIDMixin, BaseModel):
    node_license = models.ForeignKey('NodeLicense', null=True, blank=True, on_delete=models.SET_NULL)
    # Deliberately left as a CharField to support year ranges (e.g. 2012-2015)
    year = models.CharField(max_length=128, null=True, blank=True)
    copyright_holders = ArrayField(
        models.CharField(max_length=256, blank=True, null=True),
        default=list, blank=True)

    def __unicode__(self):
        if self.node_license:
            return self.node_license.__unicode__()
        return super(NodeLicenseRecord, self).__unicode__()

    @property
    def name(self):
        return self.node_license.name if self.node_license else None

    @property
    def text(self):
        return self.node_license.text if self.node_license else None

    @property
    def license_id(self):
        return self.node_license.license_id if self.node_license else None

    @property
    def url(self):
        return self.node_license.url if self.node_license else None

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
