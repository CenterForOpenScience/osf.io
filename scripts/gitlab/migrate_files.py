"""
Migrate git files from backup directories to GitLab directories. This script
should ONLY be run on the GitLab server.
"""

import os
import shutil
import subprocess


SOURCE_PATH = '/opt/data/backup/uploads'
DEST_PATH = '/opt/data/gitlab/repositories'


def migrate_files(source, dest):
    """Clone the source repo to the destination as a bare repo.

    :param str source: Source directory
    :param str dest: Destination directory

    """
    # Ensure that destination does not already exist
    shutil.rmtree(dest)

    # Clone source to destination
    try:
        subprocess.check_call(
            ['git', 'clone', '--bare', source, dest]
        )
    except subprocess.CalledProcessError as error:
        if error.returncode != 128:
            raise


def walk_repos():
    out = {}
    for user_name in os.listdir(DEST_PATH):
        user_path = os.path.join(DEST_PATH, user_name)
        if os.path.isdir(user_path):
            for repo_name in os.listdir(user_path):
                repo_path = os.path.join(user_path, repo_name)
                if os.path.isdir(repo_path):
                    repo_name_short = repo_name.split('.git')[0]
                    out[repo_name_short] = repo_path
    return out


def migrate_node(node_name, node_path, path_lookup):

    source = os.path.join(SOURCE_PATH, node_path)

    dest = path_lookup.get(node_name)
    if not dest:
        return

    migrate_files(source, dest)


def migrate_nodes():

    path_lookups = walk_repos()

    for node_name in os.listdir(SOURCE_PATH):
        node_path = os.path.join(SOURCE_PATH, node_name)
        if os.path.isdir(node_path):
            migrate_node(node_name, node_path, path_lookups)


if __name__ == '__main__':
    migrate_nodes()
