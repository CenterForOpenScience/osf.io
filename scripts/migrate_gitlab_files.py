import os
import subprocess


SOURCE_PATH = '/mount/osf'
DEST_PATH = '/mount/gitlab/repositories'

REMOTE_NAME = 'migrate'
BRANCH_NAME = 'master'


def migrate_files(source, dest):
    """Clone the source repo to the destionary as a bare repo.

    """
    # Add remote, catching exception if already added
    try:
        subprocess.check_call(
            ['git', 'remote', 'add', REMOTE_NAME, dest],
            cwd=source
        )
    except subprocess.CalledProcessError as error:
        if error.returncode != 128:
            raise

    # Push contents
    subprocess.check_call(
        ['git', 'push', REMOTE_NAME, BRANCH_NAME],
        cwd=source
    )


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
