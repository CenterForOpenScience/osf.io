from website.app import init_app

from website.addons.osffiles.model import OsfGuidFile
from website.addons.gitlab.model import GitlabGuidFile


app = init_app('website.settings', set_backends=True, routes=True)


def migrate_file_obj(file_obj):

    node_settings = file_obj.node.get_addon('gitlab')
    gitlab_obj = GitlabGuidFile.get_or_create(
        node_settings=node_settings,
        path=file_obj.path,
        client=None
    )


def migrate_file_objs():

    for osf_file_obj in OsfGuidFile.find():
        migrate_file_obj(osf_file_obj)


if __name__ == '__main__':
    migrate_file_objs()
