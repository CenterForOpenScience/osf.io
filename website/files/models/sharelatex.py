from website.util.sanitize import escape_html
from website.files.models.base import File, Folder, FileNode, FileVersion

__all__ = ('ShareLatexFile', 'ShareLatexFileNode', 'ShareLatexFolder')


class ShareLatexFileNode(FileNode):
    provider = 'sharelatex'

class ShareLatexFolder(ShareLatexFileNode, Folder):
    pass


class ShareLatexFile(ShareLatexFileNode, File):

    def touch(self, bearer, revision=None, **kwargs):
        return super(ShareLatexFile, self).touch(bearer, revision=None, **kwargs)

    def update(self, revision, data, user=None):
        """ShareLatex does not support versioning.
        Always pass revision as None to avoid conflict.
        """
        self.name = data['name']
        self.materialized_path = data['materialized']
        self.save()

        version = FileVersion(identifier=None)
        version.update_metadata(data, save=False)

        # Draft files are not renderable
        if data['extra']['status'] == 'drafts':
            return (version, u'''
            <style>
            .file-download{{display: none;}}
            .file-share{{display: none;}}
            </style>
            <div class="alert alert-info" role="alert">
            The file "{name}" is still a draft on figshare. <br>
            To view it  on the OSF <a href="http://figshare.com/faqs">publish</a> it on figshare.
            </div>
            '''.format(name=escape_html(self.name)))

        return version
