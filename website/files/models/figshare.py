import logging
import requests

from website.util.sanitize import escape_html
from website.files.models.base import File, Folder, FileNode, FileVersion


logger = logging.getLogger(__name__)
__all__ = ('FigshareFile', 'FigshareFolder', 'FigshareFileNode')


class FigshareFileNode(FileNode):
    provider = 'figshare'


class FigshareFolder(FigshareFileNode, Folder):
    pass


class FigshareFile(FigshareFileNode, File):
    def touch(self, revision=None, **kwargs):
        """Figshare does not support versioning.
        Always pass revision as None to avoid conflict.
        """

        resp = requests.get(self.generate_metadata_url(**kwargs))
        if resp.status_code != 200:
            logger.warning('Unable to find {} got status code {}'.format(self, resp.status_code))
            return None

        data = resp.json()['data']
        self.name = data['name']
        self.materialized_path = data['materialized']
        self.save()

        version = FileVersion(identifier=revision)
        version.update_metadata(data, save=False)

        # Draft files are not renderable
        if data['extra']['status'] == 'drafts':
            return (version, u'''
            <div class="alert alert-info" role="alert">
            The file "{name}" is still a draft on figshare. <br>
            To view it  on the OSF <a href="http://figshare.com/faqs">publish</a> it on figshare.
            </div>
            '''.format(name=escape_html(self.name)))

        return version
