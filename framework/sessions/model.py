from framework import StoredObject, fields, storage, db
from bson import ObjectId

class Session(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    date_created = fields.DateTimeField(auto_now_add=True)
    date_modified = fields.DateTimeField(auto_now=True)
    data = fields.DictionaryField()

Session.set_storage(storage.MongoStorage(db, 'sessions'))
