"""

"""

import datetime

from framework import GuidStoredObject, fields
from website.addons.base import AddonNodeSettingsBase


class AddonFilesNodeSettings(AddonNodeSettingsBase):

    def to_json(self, user):
        return{}


class NodeFile(GuidStoredObject):

    redirect_mode = 'redirect'

    _id = fields.StringField(primary=True)

    path = fields.StringField()
    filename = fields.StringField()
    md5 = fields.StringField()
    sha = fields.StringField()
    size = fields.IntegerField()
    content_type = fields.StringField()
    git_commit = fields.StringField()
    is_deleted = fields.BooleanField(default=False)

    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    date_uploaded = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    date_modified = fields.DateTimeField(auto_now=datetime.datetime.utcnow)

    node = fields.ForeignField('node', backref='uploads')
    uploader = fields.ForeignField('user', backref='uploads')

    @property
    def url(self):
        return '{0}osffiles/{1}/'.format(self.node.url, self.filename)

    @property
    def deep_url(self):
        return '{0}osffiles/{1}/'.format(self.node.deep_url, self.filename)

    @property
    def api_url(self):
        return '{0}osffiles/{1}/'.format(self.node.api_url, self.filename)

    @property
    def clean_filename(self):
        return self.filename.replace('.', '_')

    @property
    def latest_version_number(self):
        return len(self.node.files_versions[self.clean_filename])

    @property
    def download_url(self):
        return '{}osffiles/download/{}/version/{}/'.format(
            self.node.url, self.filename, self.latest_version_number
        )
