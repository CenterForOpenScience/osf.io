from framework import StoredObject, fields, storage
from bson import ObjectId

# todo rename to DataverseUserCredentials?
class UserSettings(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    user = fields.ForeignField('user')

    username = fields.StringField()
    password = fields.StringField()
    label = fields.StringField()

# todo rename to DataverseStudy?
class NodeSettings(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    node = fields.ForeignField('node')
    user_settings = fields.ForeignField('usersettings', list=True)

    # Allow collaborators to share credentials?
    allow_proxy_settings = fields.BooleanField()

    # Identify Network / DataVerse / Study
    hostname = fields.StringField()
    dataverse = fields.StringField()
    study_title = fields.StringField()
    study_hdl = fields.StringField()

    # Pull from DataVerse
    version = fields.IntegerField()
    is_released = fields.BooleanField()
    terms_of_service = fields.StringField()
    files = fields.ForeignField('dataversefile')

class DataverseFile(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))

    name = fields.StringField()
    size = fields.FloatField()
    checksum = fields.IntegerField()
    date_created = fields.DateTimeField()
    date_modified = fields.DateTimeField()
    download_link = fields.StringField()
    downloads = fields.IntegerField()