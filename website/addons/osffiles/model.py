"""

"""

import os
import logging
import datetime

from framework import GuidStoredObject, fields
from framework.analytics import get_basic_counters
from website.addons.base import AddonNodeSettingsBase, GuidFile


logger = logging.getLogger(__name__)


class AddonFilesNodeSettings(AddonNodeSettingsBase):

    def to_json(self, user):
        return {}


class OsfGuidFile(GuidFile):

    name = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.name is None:
            raise ValueError('Name field must be defined.')
        return os.path.join('osffiles', self.name)


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

    def latest_version_number(self, node):
        return len(node.files_versions[self.clean_filename])

    # TODO: Test me
    def download_count(self, node):
        _, total = get_basic_counters(
            'download:{0}:{1}'.format(
                node._id,
                self.path.replace('.', '_')
            )
        )
        return total or 0

    # TODO: Test me
    def version_number(self, node):
        file_versions = node.files_versions[self.clean_filename]
        version_index = file_versions.index(self._id)

        # index + 1 to account for 1-indexing of file version numbers
        return version_index + 1

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
        # Catch KeyError if file is in `files_current` but not in
        # `files_versions`
        try:
            return '{}osffiles/{}/version/{}/download/'.format(
                node.url, self.filename, self.version_number(node)
            )
        except KeyError:
            logger.error('File not found in `files_versions`')
            return self.url(node)

    def render_url(self, node):
        return '{}osffiles/{}/version/{}/render/'.format(
            node.api_url, self.filename, self.latest_version_number(node)
        )

    def info_url(self, node):
        return '{}osffiles/{}/info/'.format(
            node.api_url, self.filename
        )
