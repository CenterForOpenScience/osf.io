from modularodm import Q
from modularodm.exceptions import ModularOdmException

from website.app import init_app
from website.models import Guid

from website.addons.osffiles.model import OsfGuidFile
from website.addons.gitlab.model import GitlabGuidFile


app = init_app('website.settings', set_backends=True, routes=True)


def migrate_file_obj(file_obj):

    guid_obj = Guid.load(file_obj._id)

    try:
        gitlab_obj = GitlabGuidFile.find_one(
            Q('_id', 'eq', file_obj._id)
        )
    except ModularOdmException:
        gitlab_obj = GitlabGuidFile(_id=file_obj._id)

    gitlab_obj.node = file_obj.node
    gitlab_obj.path = file_obj.name

    gitlab_obj.save()

    guid_obj.referent = gitlab_obj
    guid_obj.save()

    return gitlab_obj


def migrate_file_objs():

    for osf_file_obj in OsfGuidFile.find():
        migrate_file_obj(osf_file_obj)


if __name__ == '__main__':
    migrate_file_objs()
