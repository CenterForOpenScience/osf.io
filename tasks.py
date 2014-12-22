#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
"""
import os
import sys
import code
import platform
import subprocess
import logging

from invoke import task, run
from invoke.exceptions import Failure

from website import settings

logging.getLogger('invoke').setLevel(logging.CRITICAL)

def get_bin_path():
    """Get parent path of current python binary.
    """
    return os.path.dirname(sys.executable)


def bin_prefix(cmd):
    """Prefix command with current binary path.
    """
    return os.path.join(get_bin_path(), cmd)


try:
    run('pip freeze | grep rednose', hide='both')
    TEST_CMD = 'nosetests --rednose'
except Failure:
    TEST_CMD = 'nosetests'


@task
def server(host=None, port=5000, debug=True):
    """Run the app server."""
    from website.app import init_app
    app = init_app(set_backends=True, routes=True)
    app.run(host=host, port=port, debug=debug)


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
    from modularodm import Q
    from framework.auth import User, Auth
    from framework.mongo import database
    from website.app import init_app
    from website.project.model import Node
    from website import models  # all models
    from website import settings
    import requests
    app = init_app()
    context = {
        'app': app,
        'db': database,
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

@task(aliases=['mongo'])
def mongoserver(daemon=False, config=None):
    """Run the mongod process.
    """
    if not config:
        platform_configs = {
            'darwin': '/usr/local/etc/tokumx.conf',  # default for homebrew install
            'linux': '/etc/tokumx.conf',
        }
        platform = str(sys.platform).lower()
        config = platform_configs.get(platform)
    port = settings.DB_PORT
    cmd = 'mongod --port {0}'.format(port)
    if config:
        cmd += ' --config {0}'.format(config)
    if daemon:
        cmd += " --fork"
    run(cmd, echo=True)


@task(aliases=['mongoshell'])
def mongoclient():
    """Run the mongo shell for the OSF database."""
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


@task(aliases=['celery'])
def celery_worker(level="debug"):
    """Run the Celery process."""
    cmd = 'celery worker -A framework.tasks -l {0}'.format(level)
    run(bin_prefix(cmd))


@task
def rabbitmq():
    """Start a local rabbitmq server.

    NOTE: this is for development only. The production environment should start
    the server as a daemon.
    """
    run("rabbitmq-server", pty=True)


@task(aliases=['elastic'])
def elasticsearch():
    """Start a local elasticsearch server

    NOTE: Requires that elasticsearch is installed. See README for instructions
    """
    import platform
    if platform.linux_distribution()[0] == 'Ubuntu':
        run("sudo service elasticsearch start")
    elif platform.system() == 'Darwin':  # Mac OSX
        run('elasticsearch')
    else:
        print("Your system is not recognized, you will have to start elasticsearch manually")

@task
def migrate_search(python='python'):
    '''Migrate the search-enabled models.'''
    cmd = '{0} -m website.search_migration.migrate'.format(python)
    run(bin_prefix(cmd))

@task
def mailserver(port=1025):
    """Run a SMTP test server."""
    cmd = 'python -m smtpd -n -c DebuggingServer localhost:{port}'.format(port=port)
    run(bin_prefix(cmd), pty=True)


@task
def flake8():
    run('flake8 .', echo=True)


@task
def requirements(all=False, download_cache=None):
    """Install dependencies."""
    cmd = "pip install --upgrade -r dev-requirements.txt"
    if download_cache:
        cmd += ' --download-cache {0}'.format(download_cache)
    run(bin_prefix(cmd), echo=True)
    if all:
        addon_requirements(download_cache=download_cache)
        mfr_requirements()


@task
def test_module(module=None, verbosity=2):
    """Helper for running tests.
    """
    # Allow selecting specific submodule
    module_fmt = ' '.join(module) if isinstance(module, list) else module
    args = " --verbosity={0} -s {1}".format(verbosity, module_fmt)
    # Use pty so the process buffers "correctly"
    run(bin_prefix(TEST_CMD) + args, pty=True)


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
def test(all=False):
    """Alias of `invoke test_osf`.
    """
    if all:
        test_all()
    else:
        test_osf()


@task
def test_all(flake=False):
    if flake:
        flake8()
    test_osf()
    test_addons()

@task
def addon_requirements(download_cache=None):
    """Install all addon requirements."""
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory)
        if os.path.isdir(path):
            try:
                requirements_file = os.path.join(path, 'requirements.txt')
                open(requirements_file)
                print('Installing requirements for {0}'.format(directory))
                cmd = 'pip install --upgrade -r {0}'.format(requirements_file)
                if download_cache:
                    cmd += ' --download-cache {0}'.format(download_cache)
                run(bin_prefix(cmd))
            except IOError:
                pass
    print('Finished')


@task
def mfr_requirements(download_cache=None):
    """Install modular file renderer requirements"""
    print('Installing mfr requirements')
    cmd = 'pip install --upgrade -r mfr/requirements.txt'
    if download_cache:
        cmd += ' --download-cache {0}'.format(download_cache)
    run(bin_prefix(cmd), echo=True)


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
    gpg = gnupg.GPG(gnupghome=settings.GNUPG_HOME, gpgbinary=settings.GNUPG_BINARY)
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
    brew_commands = [
        'update',
        'upgrade',
        'install libxml2',
        'install libxslt',
        'install elasticsearch',
        'install gpg',
        'install node',
        'tap tokutek/tokumx',
        'install tokumx-bin',
    ]
    if platform.system() == 'Darwin':
        print('Running brew commands')
        for item in brew_commands:
            command = 'brew {cmd}'.format(cmd=item)
            run(command)
    elif platform.system() == 'Linux':
        # TODO: Write a script similar to brew bundle for Ubuntu
        # e.g., run('sudo apt-get install [list of packages]')
        pass


@task
def npm_bower():
    print('Installing bower')
    run('npm install -g bower', echo=True)


@task
def bower_install():
    print('Installing bower-managed packages')
    run('bower install', echo=True)


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
def analytics():
    from scripts.analytics import (
        logs, addons, comments, links, watch, email_invites,
        permissions, profile, benchmarks
    )
    modules = (
        logs, addons, comments, links, watch, email_invites,
        permissions, profile, benchmarks
    )
    for module in modules:
        module.main()


@task
def clear_sessions(months=1, dry_run=False):
    from website.app import init_app
    init_app(routes=False, set_backends=True)
    from scripts import clear_sessions
    clear_sessions.clear_sessions_relative(months=months, dry_run=dry_run)


@task
def clear_mfr_cache():
    run('rm -rf {0}/*'.format(settings.MFR_CACHE_PATH), echo=True)


# Release tasks

@task
def hotfix(name, finish=False, push=False):
    """Rename hotfix branch to hotfix/<next-patch-version> and optionally
    finish hotfix.
    """
    print('Checking out master to calculate curent version')
    run('git checkout master')
    latest_version = latest_tag_info()['current_version']
    print('Current version is: {}'.format(latest_version))
    major, minor, patch = latest_version.split('.')
    next_patch_version = '.'.join([major, minor, str(int(patch) + 1)])
    print('Bumping to next patch version: {}'.format(next_patch_version))
    print('Renaming branch...')

    new_branch_name = 'hotfix/{}'.format(next_patch_version)
    run('git checkout {}'.format(name), echo=True)
    run('git branch -m {}'.format(new_branch_name), echo=True)
    if finish:
        run('git flow hotfix finish {}'.format(next_patch_version), echo=True, pty=True)
    if push:
        run('git push origin master', echo=True)
        run('git push --tags', echo=True)
        run('git push origin develop', echo=True)


@task
def feature(name, finish=False, push=False):
    """Rename the current branch to a feature branch and optionally finish it."""
    print('Renaming branch...')
    run('git br -m feature/{}'.format(name), echo=True)
    if finish:
        run('git flow feature finish {}'.format(name), echo=True)
    if push:
        run('git push origin develop', echo=True)


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


# Tasks for generating and bundling SSL certificates
# See http://cosdev.readthedocs.org/en/latest/osf/ops.html for details

@task
def generate_key(domain, bits=2048):
    cmd = 'openssl genrsa -des3 -out {0}.key {1}'.format(domain, bits)
    run(cmd)


@task
def generate_key_nopass(domain):
    cmd = 'openssl rsa -in {domain}.key -out {domain}.key.nopass'.format(
        domain=domain
    )
    run(cmd)


@task
def generate_csr(domain):
    cmd = 'openssl req -new -key {domain}.key.nopass -out {domain}.csr'.format(
        domain=domain
    )
    run(cmd)


@task
def request_ssl_cert(domain):
    """Generate a key, a key with password removed, and a signing request for
    the specified domain.

    Usage:
    > invoke request_ssl_cert pizza.osf.io
    """
    generate_key(domain)
    generate_key_nopass(domain)
    generate_csr(domain)


@task
def bundle_certs(domain, cert_path):
    """Concatenate certificates from NameCheap in the correct order. Certificate
    files must be in the same directory.
    """
    cert_files = [
        '{0}.crt'.format(domain),
        'COMODORSADomainValidationSecureServerCA.crt',
        'COMODORSAAddTrustCA.crt',
        'AddTrustExternalCARoot.crt',
    ]
    certs = ' '.join(
        os.path.join(cert_path, cert_file)
        for cert_file in cert_files
    )
    cmd = 'cat {certs} > {domain}.bundle.crt'.format(
        certs=certs,
        domain=domain,
    )
    run(cmd)


@task
def generate_self_signed(domain):
    """Generate self-signed SSL key and certificate.
    """
    cmd = (
        'openssl req -x509 -nodes -days 365 -newkey rsa:2048'
        ' -keyout {0}.key -out {0}.crt'
    ).format(domain)
    run(cmd)
