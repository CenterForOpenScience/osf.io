#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
'''
import os
import sys
import code
import platform

from invoke import task, run
from invoke.exceptions import Failure

from website import settings


try:
    run('pip freeze | grep rednose', hide='both')
    TEST_CMD = 'nosetests --rednose'
except Failure:
    TEST_CMD = 'nosetests'


@task
def server():
    run("python main.py")


SHELL_BANNER = """
{version}

+--------------------------------------------------+
|cccccccccccccccccccccccccccccccccccccccccccccccccc|
|ccccccccccccccccccccccOOOOOOOccccccccccccccccccccc|
|ccccccccccccccccccccOOOOOOOOOOcccccccccccccccccccc|
|cccccccccccccccccccOOOOOOOOOOOOccccccccccccccccccc|
|cccccccccOOOOOOOcccOOOOOOOOOOOOcccOOOOOOOccccccccc|
|cccccccOOOOOOOOOOccOOOOOsssOOOOcOOOOOOOOOOOccccccc|
|ccccccOOOOOOOOOOOOccOOssssssOOccOOOOOOOOOOOccccccc|
|ccccccOOOOOOOOOOOOOcOssssssssOcOOOOOOOOOOOOOcccccc|
|ccccccOOOOOOOOOOOOsOcOssssssOOOOOOOOOOOOOOOccccccc|
|cccccccOOOOOOOOOOOssccOOOOOOcOssOOOOOOOOOOcccccccc|
|cccccccccOOOOOOOsssOccccccccccOssOOOOOOOcccccccccc|
|cccccOOOccccOOssssOccccccccccccOssssOccccOOOcccccc|
|ccOOOOOOOOOOOOOccccccccccccccccccccOOOOOOOOOOOOccc|
|cOOOOOOOOssssssOcccccccccccccccccOOssssssOOOOOOOOc|
|cOOOOOOOssssssssOccccccccccccccccOsssssssOOOOOOOOc|
|cOOOOOOOOsssssssOccccccccccccccccOsssssssOOOOOOOOc|
|cOOOOOOOOOssssOOccccccccccccccccccOsssssOOOOOOOOcc|
|cccOOOOOOOOOOOOOOOccccccccccccccOOOOOOOOOOOOOOOccc|
|ccccccccccccOOssssOOccccccccccOssssOOOcccccccccccc|
|ccccccccOOOOOOOOOssOccccOOcccOsssOOOOOOOOccccccccc|
|cccccccOOOOOOOOOOOsOcOOssssOcOssOOOOOOOOOOOccccccc|
|ccccccOOOOOOOOOOOOOOOsssssssOcOOOOOOOOOOOOOOcccccc|
|ccccccOOOOOOOOOOOOOcOssssssssOcOOOOOOOOOOOOOcccccc|
|ccccccOOOOOOOOOOOOcccOssssssOcccOOOOOOOOOOOccccccc|
|ccccccccOOOOOOOOOcccOOOOOOOOOOcccOOOOOOOOOcccccccc|
|ccccccccccOOOOcccccOOOOOOOOOOOcccccOOOOccccccccccc|
|ccccccccccccccccccccOOOOOOOOOOcccccccccccccccccccc|
|cccccccccccccccccccccOOOOOOOOOcccccccccccccccccccc|
|cccccccccccccccccccccccOOOOccccccccccccccccccccccc|
|cccccccccccccccccccccccccccccccccccccccccccccccccc|
+--------------------------------------------------+

Welcome to the OSF Python Shell. Happy hacking!

Available variables:

{context}
"""


def make_shell_context():
    from framework import Q
    from framework.auth import User, Auth
    from framework import db
    from website.app import init_app
    from website.project.model import Node
    from website import models  # all models
    from website import settings
    import requests
    app = init_app()
    context = {'app': app,
                'db': db,
                'User': User,
                'Auth': Auth,
                'Node': Node,
                'Q': Q,
                'models': models,
                'run_tests': test,
                'rget': requests.get,
                'rpost': requests.post,
                'rdelete': requests.delete,
                'rput': requests.put,
                'settings': settings,
    }
    try:  # Add a fake factory for generating fake names, emails, etc.
        from faker import Factory
        fake = Factory.create()
        context['fake'] = fake
    except ImportError:
        pass
    return context


def format_context(context):
    lines = []
    for name, obj in context.items():
        line = "{name}: {obj!r}".format(**locals())
        lines.append(line)
    return '\n'.join(lines)

# Shell command adapted from Flask-Script. See NOTICE for license info.
@task
def shell():
    context = make_shell_context()
    banner = SHELL_BANNER.format(version=sys.version,
        context=format_context(context)
    )
    try:
        try:
            # 0.10.x
            from IPython.Shell import IPShellEmbed
            ipshell = IPShellEmbed(banner=banner)
            ipshell(global_ns={}, local_ns=context)
        except ImportError:
            # 0.12+
            from IPython import embed
            embed(banner1=banner, user_ns=context)
        return
    except ImportError:
        pass
    # fallback to basic python shell
    code.interact(banner, local=context)
    return

@task
def mongo(daemon=False,
          logpath="/usr/local/var/log/mongodb/mongo.log",
          logappend=True):
    """Run the mongod process.
    """
    port = settings.DB_PORT
    cmd = "mongod --port {0} --logpath {1}".format(port, logpath)
    if logappend:
        cmd += " --logappend"
    if daemon:
        cmd += " --fork"
    run(cmd)


@task
def mongoshell():
    '''Run the mongo shell for the OSF database.'''
    db = settings.DB_NAME
    port = settings.DB_PORT
    run("mongo {db} --port {port}".format(db=db, port=port), pty=True)


@task
def mongodump(path):
    """Back up the contents of the running OSF database"""
    db = settings.DB_NAME
    port = settings.DB_PORT

    cmd = "mongodump --db {db} --port {port} --out {path}".format(
        db=db,
        port=port,
        path=path,
        pty=True)

    if settings.DB_USER:
        cmd += ' --username {0}'.format(settings.DB_USER)
    if settings.DB_PASS:
        cmd += ' --password {0}'.format(settings.DB_PASS)

    run(cmd, echo=True)

    print()
    print("To restore from the dumped database, run `invoke mongorestore {0}`".format(
        os.path.join(path, settings.DB_NAME)))


@task
def mongorestore(path, drop=False):
    """Restores the running OSF database with the contents of the database at
    the location given its argument.

    By default, the contents of the specified database are added to
    the existing database. The `--drop` option will cause the existing database
    to be dropped.

    A caveat: if you `invoke mongodump {path}`, you must restore with
    `invoke mongorestore {path}/{settings.DB_NAME}, as that's where the
    database dump will be stored.
    """
    db = settings.DB_NAME
    port = settings.DB_PORT

    cmd = "mongorestore --db {db} --port {port}".format(
        db=db,
        port=port,
        pty=True)

    if settings.DB_USER:
        cmd += ' --username {0}'.format(settings.DB_USER)
    if settings.DB_PASS:
        cmd += ' --password {0}'.format(settings.DB_PASS)

    if drop:
        cmd += " --drop"

    cmd += " " + path
    run(cmd, echo=True)


@task
def celery_worker(level="debug"):
    '''Run the Celery process.'''
    run("celery worker -A framework.tasks -l {0}".format(level))


@task
def rabbitmq():
    '''Start a local rabbitmq server.

    NOTE: this is for development only. The production environment should start
    the server as a daemon.
    '''
    run("rabbitmq-server", pty=True)


@task
def elasticsearch():
    '''Start a local elasticsearch server

    NOTE: Requires that elasticsearch is installed. See README for instructions
    '''
    import platform
    if platform.linux_distribution()[0] == 'Ubuntu':
        run("sudo service elasticsearch start")
    elif platform.system() == 'Darwin': # Mac OSX
        run('elasticsearch')
    else:
        print("Your system is not recognized, you will have to start elasticsearch manually")

@task
def migrate_search(python='python'):
    '''Migrate the search-enabled models.'''
    run("{0} -m website.search_migration.migrate".format(python))

@task
def mailserver(port=1025):
    '''Run a SMTP test server.'''
    run("python -m smtpd -n -c DebuggingServer localhost:{port}".format(port=port), pty=True)


@task
def requirements(all=False):
    '''Install dependencies.'''
    run("pip install --upgrade -r dev-requirements.txt", pty=True)
    if all:
        addon_requirements()
        mfr_requirements()


@task
def test_module(module=None, verbosity=2):
    """
    Helper for running tests.
    """
    # Allow selecting specific submodule
    module_fmt = ' '.join(module) if isinstance(module, list) else module
    args = " --verbosity={0} -s {1}".format(verbosity, module_fmt)
    # Use pty so the process buffers "correctly"
    run(TEST_CMD + args, pty=True)


@task
def test_osf():
    """Run the OSF test suite."""
    test_module(module="tests/")


@task
def test_addons():
    """Run all the tests in the addons directory.
    """
    modules = []
    for addon in settings.ADDONS_REQUESTED:
        module = os.path.join(settings.BASE_PATH, 'addons', addon)
        modules.append(module)
    test_module(module=modules)


@task
def test():
    """Alias of `invoke test_osf`.
    """
    test_osf()


@task
def test_all():
    test_osf()
    test_addons()

@task
def addon_requirements():
    """Install all addon requirements."""
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory)
        if os.path.isdir(path):
            try:
                open(os.path.join(path, 'requirements.txt'))
                print('Installing requirements for {0}'.format(directory))
                run(
                    'pip install --upgrade -r {0}/{1}/requirements.txt'.format(
                        settings.ADDON_PATH,
                        directory
                    ),
                    pty=True
                )
            except IOError:
                pass
    print('Finished')


@task
def mfr_requirements():
    """Install modular file renderer requirements"""
    mfr = 'mfr'
    print('Installing mfr requirements')
    run('pip install --upgrade -r {0}/requirements.txt'.format(mfr), pty=True)


@task
def encryption(owner=None):
    """Generate GnuPG key.

    For local development:
    > invoke encryption
    On Linode:
    > sudo env/bin/invoke encryption --owner www-data

    """
    if not settings.USE_GNUPG:
        print('GnuPG is not enabled. No GnuPG key will be generated.')
        return

    import gnupg
    gpg = gnupg.GPG(gnupghome=settings.GNUPG_HOME)
    keys = gpg.list_keys()
    if keys:
        print('Existing GnuPG key found')
        return
    print('Generating GnuPG key')
    input_data = gpg.gen_key_input(name_real='OSF Generated Key')
    gpg.gen_key(input_data)
    if owner:
        run('sudo chown -R {0} {1}'.format(owner, settings.GNUPG_HOME))


@task
def travis_addon_settings():
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory, 'settings')
        if os.path.isdir(path):
            try:
                open(os.path.join(path, 'local-travis.py'))
                run('cp {path}/local-travis.py {path}/local.py'.format(path=path))
            except IOError:
                pass


@task
def copy_addon_settings():
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory, 'settings')
        if os.path.isdir(path) and not os.path.isfile(os.path.join(path, 'local.py')):
            try:
                open(os.path.join(path, 'local-dist.py'))
                run('cp {path}/local-dist.py {path}/local.py'.format(path=path))
            except IOError:
                pass


@task
def copy_settings(addons=False):
    # Website settings
    if not os.path.isfile('website/settings/local.py'):
        print('Creating local.py file')
        run('cp website/settings/local-dist.py website/settings/local.py')

    # Addon settings
    if addons:
        copy_addon_settings()


@task
def packages():
    if platform.system() == 'Darwin':
        print('Running brew bundle')
        run('brew bundle')
    elif platform.system() == 'Linux':
        # TODO: Write a script similar to brew bundle for Ubuntu
        # e.g., run('sudo apt-get install [list of packages]')
        pass


@task
def npm_bower():
    print('Installing bower')
    run('npm install -g bower')


@task
def bower_install():
    print('Installing bower-managed packages')
    run('bower install')


@task
def setup():
    """Creates local settings, installs requirements, and generates encryption key"""
    copy_settings(addons=True)
    packages()
    requirements(all=True)
    encryption()
    npm_bower()
    bower_install()


@task
def clear_mfr_cache():
    run('rm -rf {0}/*'.format(settings.MFR_CACHE_PATH), echo=True)
