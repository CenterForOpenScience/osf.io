"""

"""

import datetime

from framework import GuidStoredObject, fields
from framework.analytics import get_basic_counters
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
    def clean_filename(self):
        return self.filename.replace('.', '_')

    @property
    def latest_version_number(self):
        return len(self.node.files_versions[self.clean_filename])

    # TODO: Test me
    def download_count(self, node):
        _, total = get_basic_counters(
            'download:{0}:{1}'.format(
                node._id,
                self.path.replace('.', '_')
            )
        )
        return total or 0

    # URL methods. Note: since NodeFile objects aren't cloned on forking or
    # registration, the `node` field doesn't necessarily refer to the project
    # to which a given file is attached. These methods must take a `node`
    # parameter to build their URLs.

    def url(self, node):
        return '{0}osffiles/{1}/'.format(node.url, self.filename)

    def deep_url(self, node):
        return '{0}osffiles/{1}/'.format(node.deep_url, self.filename)

    def api_url(self, node):
        return '{0}osffiles/{1}/'.format(node.api_url, self.filename)

    def download_url(self, node):
        return '{}osffiles/download/{}/version/{}/'.format(
            node.url, self.filename, self.latest_version_number)
