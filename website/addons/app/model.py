# -*- coding: utf-8 -*-
"""Persistence layer for the app addon.
"""
from modularodm import fields

from website.search.search import update_metadata, get_mapping
from website.addons.base import AddonNodeSettingsBase

from framework.auth import User
from framework.mongo import StoredObject, ObjectId


class Metadata(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    data = fields.DictionaryField()

    app = fields.ForeignField('appnodesettings', backref='owner')

    @classmethod
    def _merge_dicts(cls, dict1, dict2):
        for key, val in dict2.items():
            if not dict1.get(key):
                dict1[key] = val
                continue

            if isinstance(val, dict):
                cls._merge_dicts(dict1[key], val)
            elif isinstance(val, list):
                dict1[key] += [index for index in val if index not in dict1[key]]
            else:
                dict1[key] = val

    @property
    def namespace(self):
        return self.app.namespace

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, val):
        self.data[key] = val

    def __delitem__(self, key):
        del self.data[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, val):
        return self._merge_dicts(self.data, val)

    def save(self):
        update_metadata(self)
        super(Metadata, self).save()

    def to_json(self):
        ret = self.data
        ret['_id'] = self._id
        return ret


class AppNodeSettings(AddonNodeSettingsBase):

    system_user = fields.ForeignField('user', backref='application')

    routes = fields.DictionaryField()
    allow_queries = fields.BooleanField(default=True)
    allow_public_read = fields.BooleanField(default=True)

    def on_add(self):

        self.owner.category = 'app'
        self.owner.save()

        system_user = User.create_confirmed(self.owner.title, '12', self.owner.title)
        system_user.is_system_user = True
        system_user.password = '12'
        system_user.save()

        self.system_user = system_user

        self.system_user.save()
        self.save()

    def _ensure_types(self, blob, metadata):
        types = get_mapping('metadata', self.namespace)

        if not types:
            return

        for key, val in blob.items():
            if not types.get(key):
                continue

            if isinstance(val, list):

                for index in val:
                    if not isinstance(index, types.get(key)):
                        raise ValueError
                continue

            if isinstance(val, types.get(key)):
                continue

            raise ValueError

    @property
    def name(self):
        # Todo possibly store this for easier querying
        return self.owner.title

    @property
    def namespace(self):
        return self._id

    @property
    def all_data(self):
        return self.metadata__data

