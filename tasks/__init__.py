#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
"""
import os
import sys
import code
import json
import platform
import subprocess
import logging
from time import sleep

import invoke
from invoke import Collection

from website import settings
from utils import pip_install, bin_prefix

logging.getLogger('invoke').setLevel(logging.CRITICAL)

# gets the root path for all the scripts that rely on it
HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WHEELHOUSE_PATH = os.environ.get('WHEELHOUSE')
CONSTRAINTS_PATH = os.path.join(HERE, 'requirements', 'constraints.txt')

try:
    __import__('rednose')
except ImportError:
    TEST_CMD = 'nosetests'
else:
    TEST_CMD = 'nosetests --rednose'

ns = Collection()

try:
    from admin import tasks as admin_tasks
    ns.add_collection(Collection.from_module(admin_tasks), name='admin')
except ImportError:
    pass


def task(*args, **kwargs):
    """Behaves the same way as invoke.task. Adds the task
    to the root namespace.
    """
    if len(args) == 1 and callable(args[0]):
        new_task = invoke.task(args[0])
        ns.add_task(new_task)
        return new_task
    def decorator(f):
        new_task = invoke.task(f, *args, **kwargs)
        ns.add_task(new_task)
        return new_task
    return decorator


@task
def server(ctx, host=None, port=5000, debug=True, live=False, gitlogs=False):
    """Run the app server."""
    if gitlogs:
        git_logs(ctx)
    from website.app import init_app
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    app = init_app(set_backends=True, routes=True)
    settings.API_SERVER_PORT = port

    if live:
        from livereload import Server
        server = Server(app.wsgi_app)
        server.watch(os.path.join(HERE, 'website', 'static', 'public'))
        server.serve(port=port)
    else:
        if settings.SECURE_MODE:
            context = (settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)
        else:
            context = None
        app.run(host=host, port=port, debug=debug, threaded=debug, extra_files=[settings.ASSET_HASH_PATH], ssl_context=context)


@task
def git_logs(ctx):
    from scripts.meta import gatherer
    gatherer.main()


@task
def apiserver(ctx, port=8000, wait=True, host='127.0.0.1'):
    """Run the API server."""
    env = os.environ.copy()
    cmd = 'DJANGO_SETTINGS_MODULE=api.base.settings {} manage.py runserver {}:{} --nothreading'\
        .format(sys.executable, host, port)
    if settings.SECURE_MODE:
        cmd = cmd.replace('runserver', 'runsslserver')
        cmd += ' --certificate {} --key {}'.format(settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)

    if wait:
        return ctx.run(cmd, echo=True, pty=True)
    from subprocess import Popen

    return Popen(cmd, shell=True, env=env)


@task
def adminserver(ctx, port=8001, host='127.0.0.1'):
    """Run the Admin server."""
    env = 'DJANGO_SETTINGS_MODULE="admin.base.settings"'
    cmd = '{} python manage.py runserver {}:{} --nothreading'.format(env, host, port)
    if settings.SECURE_MODE:
        cmd = cmd.replace('runserver', 'runsslserver')
        cmd += ' --certificate {} --key {}'.format(settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)
    ctx.run(cmd, echo=True, pty=True)


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

{transaction}
Available variables:

{context}
"""

TRANSACTION_WARNING = """
*** TRANSACTION AUTOMATICALLY STARTED ***

To persist changes run 'commit()'.
Keep in mind that changing documents will lock them.

This feature can be disabled with the '--no-transaction' flag.

"""


def make_shell_context(auto_transact=True):
    from modularodm import Q
    from framework.auth import User, Auth
    from framework.mongo import database
    from website.app import init_app
    from website.project.model import Node
    from website import models  # all models
    from website import settings
    import requests
    from framework.transactions import commands
    from framework.transactions import context as tcontext
    app = init_app()

    def commit():
        commands.commit()
        print('Transaction committed.')
        if auto_transact:
            commands.begin()
            print('New transaction opened.')

    def rollback():
        commands.rollback()
        print('Transaction rolled back.')
        if auto_transact:
            commands.begin()
            print('New transaction opened.')

    context = {
        'transaction': tcontext.TokuTransaction,
        'start_transaction': commands.begin,
        'commit': commit,
        'rollback': rollback,
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
    if auto_transact:
        commands.begin()
    return context


def format_context(context):
    lines = []
    for name, obj in context.items():
        line = '{name}: {obj!r}'.format(**locals())
        lines.append(line)
    return '\n'.join(lines)


# Shell command adapted from Flask-Script. See NOTICE for license info.
@task
def shell(ctx, transaction=True):
    context = make_shell_context(auto_transact=transaction)
    banner = SHELL_BANNER.format(version=sys.version,
        context=format_context(context),
        transaction=TRANSACTION_WARNING if transaction else ''
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
def mongoserver(ctx, daemon=False, config=None):
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
        cmd += ' --fork'
    ctx.run(cmd, echo=True)


@task(aliases=['mongoshell'])
def mongoclient(ctx):
    """Run the mongo shell for the OSF database."""
    db = settings.DB_NAME
    port = settings.DB_PORT
    ctx.run('mongo {db} --port {port}'.format(db=db, port=port), pty=True)


@task
def mongodump(ctx, path):
    """Back up the contents of the running OSF database"""
    db = settings.DB_NAME
    port = settings.DB_PORT

    cmd = 'mongodump --db {db} --port {port} --out {path}'.format(
        db=db,
        port=port,
        path=path,
        pty=True)

    if settings.DB_USER:
        cmd += ' --username {0}'.format(settings.DB_USER)
    if settings.DB_PASS:
        cmd += ' --password {0}'.format(settings.DB_PASS)

    ctx.run(cmd, echo=True)

    print()
    print('To restore from the dumped database, run `invoke mongorestore {0}`'.format(
        os.path.join(path, settings.DB_NAME)))


@task
def mongorestore(ctx, path, drop=False):
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

    cmd = 'mongorestore --db {db} --port {port}'.format(
        db=db,
        port=port,
        pty=True)

    if settings.DB_USER:
        cmd += ' --username {0}'.format(settings.DB_USER)
    if settings.DB_PASS:
        cmd += ' --password {0}'.format(settings.DB_PASS)

    if drop:
        cmd += ' --drop'

    cmd += ' ' + path
    ctx.run(cmd, echo=True)


@task
def sharejs(ctx, host=None, port=None, db_url=None, cors_allow_origin=None):
    """Start a local ShareJS server."""
    if host:
        os.environ['SHAREJS_SERVER_HOST'] = host
    if port:
        os.environ['SHAREJS_SERVER_PORT'] = port
    if db_url:
        os.environ['SHAREJS_DB_URL'] = db_url
    if cors_allow_origin:
        os.environ['SHAREJS_CORS_ALLOW_ORIGIN'] = cors_allow_origin

    if settings.SENTRY_DSN:
        os.environ['SHAREJS_SENTRY_DSN'] = settings.SENTRY_DSN

    share_server = os.path.join(settings.ADDON_PATH, 'wiki', 'shareServer.js')
    ctx.run('node {0}'.format(share_server))


@task(aliases=['celery'])
def celery_worker(ctx, level='debug', hostname=None, beat=False):
    """Run the Celery process."""
    cmd = 'celery worker -A framework.celery_tasks -l {0}'.format(level)
    if hostname:
        cmd = cmd + ' --hostname={}'.format(hostname)
    # beat sets up a cron like scheduler, refer to website/settings
    if beat:
        cmd = cmd + ' --beat'
    ctx.run(bin_prefix(cmd), pty=True)


@task(aliases=['beat'])
def celery_beat(ctx, level='debug', schedule=None):
    """Run the Celery process."""
    # beat sets up a cron like scheduler, refer to website/settings
    cmd = 'celery beat -A framework.celery_tasks -l {0} --pidfile='.format(level)
    if schedule:
        cmd = cmd + ' --schedule={}'.format(schedule)
    ctx.run(bin_prefix(cmd), pty=True)


@task
def rabbitmq(ctx):
    """Start a local rabbitmq server.

    NOTE: this is for development only. The production environment should start
    the server as a daemon.
    """
    ctx.run('rabbitmq-server', pty=True)


@task(aliases=['elastic'])
def elasticsearch(ctx):
    """Start a local elasticsearch server

    NOTE: Requires that elasticsearch is installed. See README for instructions
    """
    import platform
    if platform.linux_distribution()[0] == 'Ubuntu':
        ctx.run('sudo service elasticsearch start')
    elif platform.system() == 'Darwin':  # Mac OSX
        ctx.run('elasticsearch')
    else:
        print('Your system is not recognized, you will have to start elasticsearch manually')

@task
def migrate_search(ctx, delete=False, index=settings.ELASTIC_INDEX):
    """Migrate the search-enabled models."""
    from website.search_migration.migrate import migrate
    migrate(delete, index=index)


@task
def rebuild_search(ctx):
    """Delete and recreate the index for elasticsearch"""
    ctx.run('curl -s -XDELETE {uri}/{index}*'.format(uri=settings.ELASTIC_URI,
                                             index=settings.ELASTIC_INDEX))
    ctx.run('curl -s -XPUT {uri}/{index}'.format(uri=settings.ELASTIC_URI,
                                          index=settings.ELASTIC_INDEX))
    migrate_search(ctx)


@task
def mailserver(ctx, port=1025):
    """Run a SMTP test server."""
    cmd = 'python -m smtpd -n -c DebuggingServer localhost:{port}'.format(port=port)
    ctx.run(bin_prefix(cmd), pty=True)


@task
def jshint(ctx):
    """Run JSHint syntax check"""
    js_folder = os.path.join(HERE, 'website', 'static', 'js')
    cmd = 'jshint {}'.format(js_folder)
    ctx.run(cmd, echo=True)


@task(aliases=['flake8'])
def flake(ctx):
    ctx.run('flake8 .', echo=True)


@task(aliases=['req'])
def requirements(ctx, base=False, addons=False, release=False, dev=False, metrics=False, quick=False):
    """Install python dependencies.

    Examples:
        inv requirements
        inv requirements --quick

    Quick requirements are, in order, addons, dev and the base requirements. You should be able to use --quick for
    day to day development.

    By default, base requirements will run. However, if any set of addons, release, dev, or metrics are chosen, base
    will have to be mentioned explicitly in order to run. This is to remain compatible with previous usages. Release
    requirements will prevent dev, metrics, and base from running.
    """
    if quick:
        base = True
        addons = True
        dev = True
    if not(addons or dev or metrics):
        base = True
    if release or addons:
        addon_requirements(ctx)
    # "release" takes precedence
    if release:
        req_file = os.path.join(HERE, 'requirements', 'release.txt')
        ctx.run(
            pip_install(req_file, constraints_file=CONSTRAINTS_PATH),
            echo=True
        )
    else:
        if dev:  # then dev requirements
            req_file = os.path.join(HERE, 'requirements', 'dev.txt')
            ctx.run(
                pip_install(req_file, constraints_file=CONSTRAINTS_PATH),
                echo=True
            )
        if metrics:  # then dev requirements
            req_file = os.path.join(HERE, 'requirements', 'metrics.txt')
            ctx.run(
                pip_install(req_file, constraints_file=CONSTRAINTS_PATH),
                echo=True
            )
        if base:  # then base requirements
            req_file = os.path.join(HERE, 'requirements.txt')
            ctx.run(
                pip_install(req_file, constraints_file=CONSTRAINTS_PATH),
                echo=True
            )


@task
def test_module(ctx, module=None, verbosity=2):
    """Helper for running tests.
    """
    # Allow selecting specific submodule
    module_fmt = ' '.join(module) if isinstance(module, list) else module
    args = ' --verbosity={0} -s {1}'.format(verbosity, module_fmt)
    # Use pty so the process buffers "correctly"
    ctx.run(bin_prefix(TEST_CMD) + args, pty=True)


@task
def test_osf(ctx):
    """Run the OSF test suite."""
    test_module(ctx, module='tests/')


@task
def test_api(ctx):
    """Run the API test suite."""
    test_module(ctx, module='api_tests/')


@task
def test_admin(ctx):
    """Run the Admin test suite."""
    # test_module(ctx, module="admin_tests/")
    module = 'admin_tests/'
    module_fmt = ' '.join(module) if isinstance(module, list) else module
    admin_tasks.manage(ctx, 'test {}'.format(module_fmt))


@task
def test_varnish(ctx):
    """Run the Varnish test suite."""
    proc = apiserver(ctx, wait=False)
    sleep(5)
    test_module(ctx, module='api/caching/tests/test_caching.py')
    proc.kill()


@task
def test_addons(ctx):
    """Run all the tests in the addons directory.
    """
    modules = []
    for addon in settings.ADDONS_REQUESTED:
        module = os.path.join(settings.BASE_PATH, 'addons', addon)
        modules.append(module)
    test_module(ctx, module=modules)


@task
def test(ctx, all=False, syntax=False):
    """
    Run unit tests: OSF (always), plus addons and syntax checks (optional)
    """
    if syntax:
        flake(ctx)
        jshint(ctx)

    test_osf(ctx)
    test_api(ctx)
    test_admin(ctx)

    if all:
        test_addons(ctx)
        karma(ctx, single=True, browsers='PhantomJS')


@task
def test_travis_osf(ctx):
    """
    Run half of the tests to help travis go faster
    """
    flake(ctx)
    jshint(ctx)
    test_osf(ctx)

@task
def test_travis_else(ctx):
    """
    Run other half of the tests to help travis go faster
    """
    test_addons(ctx)
    test_api(ctx)
    test_admin(ctx)
    karma(ctx, single=True, browsers='PhantomJS')


@task
def test_travis_varnish(ctx):
    test_varnish(ctx)


@task
def karma(ctx, single=False, sauce=False, browsers=None):
    """Run JS tests with Karma. Requires Chrome to be installed."""
    karma_bin = os.path.join(
        HERE, 'node_modules', 'karma', 'bin', 'karma'
    )
    cmd = '{} start'.format(karma_bin)
    if sauce:
        cmd += ' karma.saucelabs.conf.js'
    if single:
        cmd += ' --single-run'
    # Use browsers if specified on the command-line, otherwise default
    # what's specified in karma.conf.js
    if browsers:
        cmd += ' --browsers {}'.format(browsers)
    ctx.run(cmd, echo=True)


@task
def wheelhouse(ctx, addons=False, release=False, dev=False, metrics=False):
    """Build wheels for python dependencies.

    Examples:

        inv wheelhouse --dev
        inv wheelhouse --addons
        inv wheelhouse --release
        inv wheelhouse --metrics
    """
    if release or addons:
        for directory in os.listdir(settings.ADDON_PATH):
            path = os.path.join(settings.ADDON_PATH, directory)
            if os.path.isdir(path):
                req_file = os.path.join(path, 'requirements.txt')
                if os.path.exists(req_file):
                    cmd = 'pip wheel --find-links={} -r {} --wheel-dir={}'.format(WHEELHOUSE_PATH, req_file, WHEELHOUSE_PATH)
                    ctx.run(cmd, pty=True)
    if release:
        req_file = os.path.join(HERE, 'requirements', 'release.txt')
    elif dev:
        req_file = os.path.join(HERE, 'requirements', 'dev.txt')
    elif metrics:
        req_file = os.path.join(HERE, 'requirements', 'metrics.txt')
    else:
        req_file = os.path.join(HERE, 'requirements.txt')
    cmd = 'pip wheel --find-links={} -r {} --wheel-dir={}'.format(WHEELHOUSE_PATH, req_file, WHEELHOUSE_PATH)
    ctx.run(cmd, pty=True)


@task
def addon_requirements(ctx):
    """Install all addon requirements."""
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory)

        requirements_file = os.path.join(path, 'requirements.txt')
        if os.path.isdir(path) and os.path.isfile(requirements_file):
            print('Installing requirements for {0}'.format(directory))
            ctx.run(
                pip_install(requirements_file, constraints_file=CONSTRAINTS_PATH),
                echo=True
            )

    print('Finished installing addon requirements')


@task
def encryption(ctx, owner=None):
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
        ctx.run('sudo chown -R {0} {1}'.format(owner, settings.GNUPG_HOME))


@task
def travis_addon_settings(ctx):
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory, 'settings')
        if os.path.isdir(path):
            try:
                open(os.path.join(path, 'local-travis.py'))
                ctx.run('cp {path}/local-travis.py {path}/local.py'.format(path=path))
            except IOError:
                pass


@task
def copy_addon_settings(ctx):
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory, 'settings')
        if os.path.isdir(path) and not os.path.isfile(os.path.join(path, 'local.py')):
            try:
                open(os.path.join(path, 'local-dist.py'))
                ctx.run('cp {path}/local-dist.py {path}/local.py'.format(path=path))
            except IOError:
                pass


@task
def copy_settings(ctx, addons=False):
    # Website settings
    if not os.path.isfile('website/settings/local.py'):
        print('Creating local.py file')
        ctx.run('cp website/settings/local-dist.py website/settings/local.py')

    # Addon settings
    if addons:
        copy_addon_settings(ctx)


@task
def packages(ctx):
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
            ctx.run(command)
    elif platform.system() == 'Linux':
        # TODO: Write a script similar to brew bundle for Ubuntu
        # e.g., run('sudo apt-get install [list of packages]')
        pass


@task(aliases=['bower'])
def bower_install(ctx):
    print('Installing bower-managed packages')
    bower_bin = os.path.join(HERE, 'node_modules', 'bower', 'bin', 'bower')
    ctx.run('{} prune'.format(bower_bin), echo=True)
    ctx.run('{} install'.format(bower_bin), echo=True)


@task
def setup(ctx):
    """Creates local settings, installs requirements, and generates encryption key"""
    copy_settings(ctx, addons=True)
    packages(ctx)
    requirements(ctx, addons=True, dev=True)
    encryption(ctx)
    # Build nodeCategories.json before building assets
    build_js_config_files(ctx)
    assets(ctx, dev=True, watch=False)


@task
def clear_sessions(ctx, months=1, dry_run=False):
    from website.app import init_app
    init_app(routes=False, set_backends=True)
    from scripts import clear_sessions
    clear_sessions.clear_sessions_relative(months=months, dry_run=dry_run)


# Release tasks

@task
def hotfix(ctx, name, finish=False, push=False):
    """Rename hotfix branch to hotfix/<next-patch-version> and optionally
    finish hotfix.
    """
    print('Checking out master to calculate curent version')
    ctx.run('git checkout master')
    latest_version = latest_tag_info()['current_version']
    print('Current version is: {}'.format(latest_version))
    major, minor, patch = latest_version.split('.')
    next_patch_version = '.'.join([major, minor, str(int(patch) + 1)])
    print('Bumping to next patch version: {}'.format(next_patch_version))
    print('Renaming branch...')

    new_branch_name = 'hotfix/{}'.format(next_patch_version)
    ctx.run('git checkout {}'.format(name), echo=True)
    ctx.run('git branch -m {}'.format(new_branch_name), echo=True)
    if finish:
        ctx.run('git flow hotfix finish {}'.format(next_patch_version), echo=True, pty=True)
    if push:
        ctx.run('git push origin master', echo=True)
        ctx.run('git push --tags', echo=True)
        ctx.run('git push origin develop', echo=True)


@task
def feature(ctx, name, finish=False, push=False):
    """Rename the current branch to a feature branch and optionally finish it."""
    print('Renaming branch...')
    ctx.run('git branch -m feature/{}'.format(name), echo=True)
    if finish:
        ctx.run('git flow feature finish {}'.format(name), echo=True)
    if push:
        ctx.run('git push origin develop', echo=True)


# Adapted from bumpversion
def latest_tag_info():
    try:
        # git-describe doesn't update the git-index, so we do that
        # subprocess.check_output(["git", "update-index", "--refresh"])

        # get info about the latest tag in git
        describe_out = subprocess.check_output([
            'git',
            'describe',
            '--dirty',
            '--tags',
            '--long',
            '--abbrev=40'
        ], stderr=subprocess.STDOUT
        ).decode().split('-')
    except subprocess.CalledProcessError as err:
        raise err
        # logger.warn("Error when running git describe")
        return {}

    info = {}

    if describe_out[-1].strip() == 'dirty':
        info['dirty'] = True
        describe_out.pop()

    info['commit_sha'] = describe_out.pop().lstrip('g')
    info['distance_to_latest_tag'] = int(describe_out.pop())
    info['current_version'] = describe_out.pop().lstrip('v')

    # assert type(info["current_version"]) == str
    assert 0 == len(describe_out)

    return info


# Tasks for generating and bundling SSL certificates
# See http://cosdev.readthedocs.org/en/latest/osf/ops.html for details

@task
def generate_key(ctx, domain, bits=2048):
    cmd = 'openssl genrsa -des3 -out {0}.key {1}'.format(domain, bits)
    ctx.run(cmd)


@task
def generate_key_nopass(ctx, domain):
    cmd = 'openssl rsa -in {domain}.key -out {domain}.key.nopass'.format(
        domain=domain
    )
    ctx.run(cmd)


@task
def generate_csr(ctx, domain):
    cmd = 'openssl req -new -key {domain}.key.nopass -out {domain}.csr'.format(
        domain=domain
    )
    ctx.run(cmd)


@task
def request_ssl_cert(ctx, domain):
    """Generate a key, a key with password removed, and a signing request for
    the specified domain.

    Usage:
    > invoke request_ssl_cert pizza.osf.io
    """
    generate_key(ctx, domain)
    generate_key_nopass(ctx, domain)
    generate_csr(ctx, domain)


@task
def bundle_certs(ctx, domain, cert_path):
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
    ctx.run(cmd)


@task
def clean_assets(ctx):
    """Remove built JS files."""
    public_path = os.path.join(HERE, 'website', 'static', 'public')
    js_path = os.path.join(public_path, 'js')
    ctx.run('rm -rf {0}'.format(js_path), echo=True)


@task(aliases=['pack'])
def webpack(ctx, clean=False, watch=False, dev=False, colors=False):
    """Build static assets with webpack."""
    if clean:
        clean_assets(ctx)
    webpack_bin = os.path.join(HERE, 'node_modules', 'webpack', 'bin', 'webpack.js')
    args = [webpack_bin]
    args += ['--progress']
    if watch:
        args += ['--watch']
    if colors:
        args += ['--colors']
    config_file = 'webpack.dev.config.js' if dev else 'webpack.prod.config.js'
    args += ['--config {0}'.format(config_file)]
    command = ' '.join(args)
    ctx.run(command, echo=True)


@task()
def build_js_config_files(ctx):
    from website import settings
    print('Building JS config files...')
    with open(os.path.join(settings.STATIC_FOLDER, 'built', 'nodeCategories.json'), 'wb') as fp:
        json.dump(settings.NODE_CATEGORY_MAP, fp)
    print('...Done.')


@task()
def assets(ctx, dev=False, watch=False, colors=False):
    """Install and build static assets."""
    npm = 'npm install'
    if not dev:
        npm += ' --production'
    ctx.run(npm, echo=True)
    bower_install(ctx)
    build_js_config_files(ctx)
    # Always set clean=False to prevent possible mistakes
    # on prod
    webpack(ctx, clean=False, watch=watch, dev=dev, colors=colors)


@task
def generate_self_signed(ctx, domain):
    """Generate self-signed SSL key and certificate.
    """
    cmd = (
        'openssl req -x509 -nodes -days 365 -newkey rsa:2048'
        ' -keyout {0}.key -out {0}.crt'
    ).format(domain)
    ctx.run(cmd)


@task
def update_citation_styles(ctx):
    from scripts import parse_citation_styles
    total = parse_citation_styles.main()
    print('Parsed {} styles'.format(total))


@task
def clean(ctx, verbose=False):
    ctx.run('find . -name "*.pyc" -delete', echo=True)


@task(default=True)
def usage(ctx):
    ctx.run('invoke --list')


### Maintenance Tasks ###

@task
def set_maintenance(ctx, start=None, end=None):
    from website.maintenance import set_maintenance, get_maintenance
    """Set the time period for the maintenance notice to be displayed.
    If no start or end values are displayed, default to starting now
    and ending 24 hours from now. If no timezone info is passed along,
    everything will be converted to UTC.

    If a given end time results in a start that is after the end, start
    will be changed to be 24 hours before the end time.

    Examples:
        invoke set_maintenance_state
        invoke set_maintenance_state --start 2016-03-16T15:41:00-04:00
        invoke set_maintenance_state --end 2016-03-16T15:41:00-04:00
    """
    set_maintenance(start, end)
    state = get_maintenance()
    print('Maintenance notice up for {} to {}.'.format(state['start'], state['end']))


@task
def unset_maintenance(ctx):
    from website.maintenance import unset_maintenance
    print('Taking down maintenance notice...')
    unset_maintenance()
    print('...Done.')
