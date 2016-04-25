# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os

from invoke import task, run

from website import settings

HERE = os.path.dirname(os.path.abspath(__file__))
WHEELHOUSE_PATH = os.environ.get('WHEELHOUSE')


@task()
def manage(cmd_str):
    """Take command string for manage commands

    :param cmd_str: ex. runserver, migrate, "migrate module"
    """
    manage_cmd = os.path.join(HERE, '..', 'manage.py')
    env = 'DJANGO_SETTINGS_MODULE="admin.base.settings"'
    cmd = '{} python {} {}'.format(env, manage_cmd, cmd_str)
    run(cmd, echo=True, pty=True)


@task()
def assets(dev=False, watch=False):
    """Install and build static assets for admin.

    use -d for dev environments
    """
    if os.getcwd() != HERE:
        os.chdir(HERE)
    npm = 'npm install'
    if not dev:
        npm += ' --production'
    run(npm, echo=True)
    bower_install()
    # Always set clean=False to prevent possible mistakes
    # on prod
    webpack(clean=False, watch=watch, dev=dev)


@task(aliases=['pack'])
def webpack(clean=False, watch=False, dev=False):
    """Build static assets with webpack."""
    if clean:
        clean_assets()
    if os.getcwd() != HERE:
        os.chdir(HERE)
    webpack_bin = os.path.join(HERE, 'node_modules', 'webpack', 'bin',
                               'webpack.js')
    args = [webpack_bin]
    if settings.DEBUG_MODE and dev:
        args += ['--colors']
    else:
        args += ['--progress']
    if watch:
        args += ['--watch']
    config_file = 'webpack.admin.config.js' if dev else 'webpack.prod.config.js'
    args += ['--config {0}'.format(config_file)]
    command = ' '.join(args)
    run(command, echo=True)


@task
def clean_assets():
    """Remove built JS files."""
    public_path = os.path.join(HERE, 'static', 'public')
    js_path = os.path.join(public_path, 'js')
    run('rm -rf {0}'.format(js_path), echo=True)


@task(aliases=['bower'])
def bower_install():
    if os.getcwd() != HERE:
        os.chdir(HERE)
    bower_bin = os.path.join(HERE, 'node_modules', 'bower', 'bin', 'bower')
    run('{} prune'.format(bower_bin), echo=True)
    run('{} install'.format(bower_bin), echo=True)
