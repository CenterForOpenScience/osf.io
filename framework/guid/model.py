# -*- coding: utf-8 -*-
from modularodm import fields
from framework.mongo import StoredObject, ObjectId


# Placed here because there is no other good place to go
# Todo have a reference back to guid?
class Metadata(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    data = fields.DictionaryField()
    guid = fields.StringField()
    app = fields.ForeignField('appnodesettings', backref='data')

    @classmethod
    def _merge_dicts(cls, dict1, dict2):
        for key, val in dict2.items():
            if not dict1.get(key):
                dict1[key] = val
                continue

            if isinstance(val, dict):
                cls._merge_dicts(dict1[key], val)
            elif isinstance(val, list):
                dict1[key] += [index for index in val if not index in dict1[key]]
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

    def to_json(self):
        ret = {
            'guid': self.guid  # TODO
        }
        ret.update(self.data)
        return ret


class Guid(StoredObject):

    _id = fields.StringField()
    referent = fields.AbstractForeignField()
    metastore = fields.DictionaryField()

    _meta = {
        'optimistic': True,
    }

    def __getitem__(self, app):
        metadata = Metadata.load(self.metastore.get(app.namespace))

        if not metadata:
            metadata = Metadata(app=app, guid=self._id)
            metadata.save()
            self.metastore[app.namespace] = metadata._id
            self.save()

        return metadata

    def __repr__(self):
        return '<id:{0}, referent:({1}, {2})>'.format(self._id, self.referent._primary_key, self.referent._name)


class GuidStoredObject(StoredObject):

    def __str__(self):
        return str(self._id)

    # Redirect to content using URL redirect by default
    redirect_mode = 'redirect'

    def _ensure_guid(self):
        """Create GUID record if current record doesn't already have one, then
        point GUID to self.

        """
        # Create GUID with specified ID if ID provided
        if self._primary_key:

            # Done if GUID already exists
            guid = Guid.load(self._primary_key)
            if guid is not None:
                return

            # Create GUID
            guid = Guid(
                _id=self._primary_key,
                referent=self
            )
            guid.save()

        # Else create GUID optimistically
        else:

            # Create GUID
            guid = Guid()
            guid.save()
            guid.referent = (guid._primary_key, self._name)
            guid.save()

            # Set primary key to GUID key
            self._primary_key = guid._primary_key

    def save(self, *args, **kwargs):
        """ Ensure GUID on save initialization. """
        self._ensure_guid()
        return super(GuidStoredObject, self).save(*args, **kwargs)

    @property
    def annotations(self):
        """ Get meta-data annotations associated with object. """
        return self.metadata__annotated
