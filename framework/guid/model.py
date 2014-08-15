from framework import StoredObject, fields
from framework.mongo import ObjectId


# Placed here because there is no other good place to go
# Todo have a reference back to guid?
class Metadata(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    data = fields.DictionaryField()
    # guid = fields.ForeignField('guid', backref='metadata')

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
        return self.data.update(val)

    def to_json(self):
        return self.data


class Guid(StoredObject):

    _id = fields.StringField()
    referent = fields.AbstractForeignField()
    metastore = fields.DictionaryField()

    _meta = {
        'optimistic': True,
    }

    def __getitem__(self, key):
        metadata = Metadata.load(self.metastore.get(key))

        if metadata:
            return metadata

        metadata = Metadata()
        metadata.save()
        self.metastore[key] = metadata._id
        self.save()
        return metadata


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
