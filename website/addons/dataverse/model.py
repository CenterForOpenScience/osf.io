from framework import StoredObject, fields, storage
from framework import db
from bson import ObjectId

class DataverseUserSettings(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    user = fields.ForeignField('user')

    network_title = fields.StringField()
    network_uri = fields.StringField()
    username = fields.StringField()
    password = fields.StringField()
    label = fields.StringField()

DataverseUserSettings.set_storage(storage.MongoStorage(db, 'dataverseusersettings'))

class DataverseNodeSettings(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    node = fields.ForeignField('node')
    user_settings = fields.ForeignField('DataverseUserSettings', list=True)

    # Allow collaborators to share credentials?
    allow_proxy_settings = fields.BooleanField()

    # Identify Network / DataVerse / Study
    network_title = fields.StringField()
    network_uri = fields.StringField()
    dataverse_name = fields.StringField()
    dataverse_alias = fields.StringField()
    study_title = fields.StringField()
    study_global_id = fields.StringField()

    # Pull from DataVerse
    version = fields.IntegerField()
    is_dataverse_released = fields.BooleanField()
    is_study_released = fields.BooleanField()
    terms_of_service = fields.StringField()
    files = fields.ForeignField('DataverseFile')

DataverseNodeSettings.set_storage(storage.MongoStorage(db, 'dataversenodesettings'))

class DataverseFile(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))

    name = fields.StringField()
    size = fields.FloatField()
    mimetype = fields.StringField()
    checksum = fields.IntegerField()
    edit_media_uri = fields.StringField()
    date_created = fields.DateTimeField()
    date_modified = fields.DateTimeField()
    download_url = fields.StringField()
    download_count = fields.IntegerField()

    # def get_download_link(self):
    #     pass

DataverseFile.set_storage(storage.MongoStorage(db, 'dataversefile'))