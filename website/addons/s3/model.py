from framework import StoredObject, fields
from bson import ObjectId

class S3UserSettings(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    user = fields.ForeignField('User')

    aws_access_key_id = fields.StringField()
    aws_secret_access_key = fields.StringField()
    label = fields.StringField()

class S3NodeSettings(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    node = fields.ForeignField('Node')
    user_info = fields.ForeignField('S3UserSettings', list=True)

    # Allow collaborators to share credentials?
    allow_proxy_settings = fields.BooleanField()

    bucket = fields.StringField()
    files = fields.ForeignField('S3File', list=True)

class S3File(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))

    key = fields.StringField()
    date_created = fields.DateTimeField()
    date_modified = fields.DateTimeField()