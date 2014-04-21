"""
Identify all existing OSF file objects with GUIDs and point them to the
corresponding GitLab file objects. This script should ONLY be run on the app
machine.
"""

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from website.app import init_app
from website.models import Guid

from website.addons.osffiles.model import OsfGuidFile
from website.addons.gitlab.model import GitlabGuidFile


app = init_app('website.settings', set_backends=True, routes=True)


def migrate_file_obj(file_obj):
    """Migrate a file object from OSF files to GitLab.

    """
    # Get GUID object
    guid_obj = Guid.load(file_obj._id)

    # Get or create GitLab file object
    try:
        gitlab_obj = GitlabGuidFile.find_one(
            Q('_id', 'eq', file_obj._id)
        )
    except ModularOdmException:
        gitlab_obj = GitlabGuidFile(_id=file_obj._id)

    # Copy OSF file object parameters
    gitlab_obj.node = file_obj.node
    gitlab_obj.path = file_obj.name
    gitlab_obj.save()

    # Point GUID object to GitLab file object
    guid_obj.referent = gitlab_obj
    guid_obj.save()

    return gitlab_obj


def migrate_file_objs():
    """Migrate all OSF file objects."""
    for osf_file_obj in OsfGuidFile.find():
        migrate_file_obj(osf_file_obj)


if __name__ == '__main__':
    migrate_file_objs()
