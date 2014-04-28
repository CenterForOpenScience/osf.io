import os
import logging
import subprocess

from website import settings
from website.addons.osffiles.model import NodeFile


logger = logging.getLogger(__name__)


def get_node_path(node):
    return os.path.join(settings.UPLOADS_PATH, node._id)


def get_commits(node, file=None):

    try:
        cmd_args = ['git', 'rev-list', '--all', '--reverse']
        if file:
            cmd_args.append(file)
        output = subprocess.check_output(
            cmd_args,
            cwd=get_node_path(node)
        )
    except subprocess.CalledProcessError as error:
        logger.error(error)
        raise
        # if error.status_code ...
        # return []

    return output.strip().split('\n')


def get_mongo_commits(node):

    out = {}

    for name, versions in node.files_versions.iteritems():
        out[name] = []
        for fid in versions:
            fobj = NodeFile.load(fid)
            if fobj and fobj.git_commit:
                out[name].append(fobj.git_commit)

    return out
