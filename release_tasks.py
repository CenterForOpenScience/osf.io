# -*- coding: utf-8 -*-
"""Release-related invoke tasks."""
import subprocess

from invoke import task, run

@task
def hotfix(name=None, finish=False):
    """Rename current hotfix branch to hotfix/<next-patch-version> and optionally
    finish hotfix.
    """
    if name:
        run('git checkout hotfix/{}'.format(name), echo=True)
    latest_version = latest_tag_info()['current_version']
    print('Current version is; {}'.format(latest_version))
    major, minor, patch = latest_version.split('.')
    next_patch_version = '.'.join([major, minor, str(int(patch) + 1)])
    print('Bumping to next patch version: {}'.format(next_patch_version))
    print('Renaming branch...')

    new_branch_name = 'hotfix/{}'.format(next_patch_version)

    run('git branch -m {}'.format(new_branch_name), echo=True)
    if finish:
        run('git flow finish {}'.format(next_patch_version), echo=True)

# Adapted from bumpversion
def latest_tag_info():
    try:
        # git-describe doesn't update the git-index, so we do that
        # subprocess.check_output(["git", "update-index", "--refresh"])

        # get info about the latest tag in git
        describe_out = subprocess.check_output([
            "git",
            "describe",
            "--dirty",
            "--tags",
            "--long",
            "--abbrev=40"
        ], stderr=subprocess.STDOUT
        ).decode().split("-")
    except subprocess.CalledProcessError as err:
        raise err
        # logger.warn("Error when running git describe")
        return {}

    info = {}

    if describe_out[-1].strip() == "dirty":
        info["dirty"] = True
        describe_out.pop()

    info["commit_sha"] = describe_out.pop().lstrip("g")
    info["distance_to_latest_tag"] = int(describe_out.pop())
    info["current_version"] = describe_out.pop().lstrip("v")

    # assert type(info["current_version"]) == str
    assert 0 == len(describe_out)

    return info
