import markupsafe

from website.files.models.base import File, Folder, FileNode, FileVersion


__all__ = ('FigshareFile', 'FigshareFolder', 'FigshareFileNode')


class FigshareFileNode(FileNode):
    provider = 'figshare'


class FigshareFolder(FigshareFileNode, Folder):
    pass


class FigshareFile(FigshareFileNode, File):

    def touch(self, bearer, revision=None, **kwargs):
        return super(FigshareFile, self).touch(bearer, revision=None, **kwargs)

    def update(self, revision, data, user=None):
        """Figshare does not support versioning.
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
            To view it  on the OSF
            <a href="https://support.figshare.com/support/solutions ">publish</a>
            it on figshare.
            </div>
            '''.format(name=markupsafe.escape(self.name)))

        return version
