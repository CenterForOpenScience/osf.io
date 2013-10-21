from framework import StoredObject, fields
from . import make_encoded_snowflake

class Guid(StoredObject):

    _id = fields.StringField(default=make_encoded_snowflake)
    referent = fields.AbstractForeignField(backref='guid')


class GuidStoredObject(StoredObject):

    def __init__(self, *args, **kwargs):

        # Call superclass constructor
        super(GuidStoredObject, self).__init__(*args, **kwargs)

        # Done if primary key exists
        if self._primary_key:
            return

        # Create GUID
        guid = Guid()
        guid.save()

        # Set primary key to GUID key
        self._primary_key = guid._primary_key
        self.save()

        # Add self to GUID
        guid.referent = self
        guid.save()
