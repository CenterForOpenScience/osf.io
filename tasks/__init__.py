#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
"""
import os
import sys
import json
import platform
import subprocess
import logging
import sqlite3

import invoke
from invoke import Collection

from website import settings
from .utils import pip_install, bin_prefix


try:
    from tasks import local  # noqa
except ImportError:
    print('No tasks/local.py file found. '
          'Did you remember to copy local-dist.py to local.py?')

logging.getLogger('invoke').setLevel(logging.CRITICAL)

# gets the root path for all the scripts that rely on it
HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WHEELHOUSE_PATH = os.environ.get('WHEELHOUSE')
NO_TESTS_COLLECTED = 5
ns = Collection()

try:
    from tasks import local as local_tasks
    ns.add_collection(Collection.from_module(local_tasks), name='local')
except ImportError:
    pass

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
def server(ctx, host=None, port=5000, debug=True, gitlogs=False):
    """Run the app server."""

    sys.setrecursionlimit(settings.RECURSION_LIMIT)  # [GRDM-9050, GRDM-16889]

    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not debug:
        if os.environ.get('WEB_REMOTE_DEBUG', None):
            import pydevd
            # e.g. '127.0.0.1:5678'
            remote_parts = os.environ.get('WEB_REMOTE_DEBUG').split(':')
            pydevd.settrace(remote_parts[0], port=int(remote_parts[1]), suspend=False, stdoutToServer=True, stderrToServer=True)

        if gitlogs:
            git_logs(ctx)
        from website.app import init_app
        os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
        app = init_app(set_backends=True, routes=True)
        settings.API_SERVER_PORT = port

    else:
        from framework.flask import app

    context = None
    if settings.SECURE_MODE:
        context = (settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)
    app.run(host=host, port=port, debug=debug, threaded=debug, extra_files=[settings.ASSET_HASH_PATH], ssl_context=context)


@task
def reset_user(ctx, username=None):
    from website.app import init_app
    init_app(routes=False, set_backends=False)

    from osf.models import OSFUser

    if username is None:
        print('usage: invoke reset_user -u <username>')
        print('OSF users (username):')
        for user in OSFUser.objects.all():
            print(user.username)
        return

    try:
        user = OSFUser.objects.get(username=username)
    except Exception as ex:
        print(ex)
        user = None
    if user is None:
        print('no such user: ' + username)
        return

    try:
        nodes = user.nodes.filter()
    except Exception as ex:
        print(ex)
        nodes = None

    if nodes is not None:
        for node in nodes:
            print('Node Contributor: GUID={}, title={}'.format(node._id, node.title))

    user.emails.filter(address=user.username).delete()

    user.have_email = False

    dummy = user.username
    for i in range(1000):
        dummy = '__dummy_' + str(i) + '__' + user.username
        if not OSFUser.objects.filter(username=dummy).exists():
            break

    user.username = dummy.lower().strip()
    user.emails.filter(address=user.username).delete()
    if not user.emails.filter(address=user.username):
        user.emails.create(address=user.username)
    user.save()
    print('reset_user OK: ' + username)


@task
def git_logs(ctx, branch=None):
    from scripts.meta import gatherer
    gatherer.main(branch=branch)


@task
def apiserver(ctx, port=8000, wait=True, autoreload=True, host='127.0.0.1', pty=True):
    """Run the API server."""
    env = os.environ.copy()
    cmd = 'DJANGO_SETTINGS_MODULE=api.base.settings {} manage.py runserver {}:{} --nothreading'\
        .format(sys.executable, host, port)
    if not autoreload:
        cmd += ' --noreload'
    if settings.SECURE_MODE:
        cmd = cmd.replace('runserver', 'runsslserver')
        cmd += ' --certificate {} --key {}'.format(settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)

    if wait:
        return ctx.run(cmd, echo=True, pty=pty)
    from subprocess import Popen

    return Popen(cmd, shell=True, env=env)


@task
def adminserver(ctx, port=8001, host='127.0.0.1', pty=True):
    """Run the Admin server."""
    env = 'DJANGO_SETTINGS_MODULE="admin.base.settings"'
    cmd = '{} python3 manage.py runserver {}:{} --nothreading'.format(env, host, port)
    if settings.SECURE_MODE:
        cmd = cmd.replace('runserver', 'runsslserver')
        cmd += ' --certificate {} --key {}'.format(settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)
    ctx.run(cmd, echo=True, pty=pty)

@task
def shell(ctx, transaction=True, print_sql=False, notebook=False):
    cmd = 'DJANGO_SETTINGS_MODULE="api.base.settings" python3 manage.py osf_shell'
    if print_sql:
        cmd += ' --print-sql'
    if notebook:
        cmd += ' --notebook'
    if not transaction:
        cmd += ' --no-transaction'
    return ctx.run(cmd, pty=True, echo=True)


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
def celery_worker(ctx, level='debug', hostname=None, beat=False, queues=None, concurrency=None, max_tasks_per_child=None):
    """Run the Celery process."""
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    cmd = 'celery worker -A framework.celery_tasks -Ofair -l {0}'.format(level)
    if hostname:
        cmd = cmd + ' --hostname={}'.format(hostname)
    # beat sets up a cron like scheduler, refer to website/settings
    if beat:
        cmd = cmd + ' --beat'
    if queues:
        cmd = cmd + ' --queues={}'.format(queues)
    if concurrency:
        cmd = cmd + ' --concurrency={}'.format(concurrency)
    if max_tasks_per_child:
        cmd = cmd + ' --maxtasksperchild={}'.format(max_tasks_per_child)
    from addons.base.lock_utils import init_lock
    init_lock()
    ctx.run(bin_prefix(cmd), pty=True)


@task(aliases=['beat'])
def celery_beat(ctx, level='debug', schedule=None):
    """Run the Celery process."""
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    # beat sets up a cron like scheduler, refer to website/settings
    cmd = 'celery beat -A framework.celery_tasks -l {0} --pidfile='.format(level)
    if schedule:
        cmd = cmd + ' --schedule={}'.format(schedule)
    ctx.run(bin_prefix(cmd), pty=True)

@task
def migrate_search(ctx, delete=True, remove=False, remove_all=False, index=None):
    """Migrate the search-enabled models."""
    from website.app import init_app
    init_app(routes=False, set_backends=False)
    from website.search_migration.migrate import migrate

    # NOTE: Silence the warning:
    # "InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised."
    SILENT_LOGGERS = ['py.warnings']
    for logger in SILENT_LOGGERS:
        logging.getLogger(logger).setLevel(logging.ERROR)

    migrate(delete, remove=remove, remove_all=remove_all, index=index)

@task
def rebuild_search(ctx):
    """Delete and recreate the index for elasticsearch"""
    from website.app import init_app

    init_app(routes=False, set_backends=True)

    # remove_all=True for development
    migrate_search(ctx, delete=False, remove=True, remove_all=False)


@task
def mailserver(ctx, host='localhost', port=1025):
    """Run a SMTP test server."""
    cmd = 'python3 -m smtpd -n -c DebuggingServer {host}:{port}'.format(host=host, port=port)
    ctx.run(bin_prefix(cmd), pty=True)


@task
def syntax(ctx):
    """Use pre-commit to run formatters and linters."""
    ctx.run('pre-commit run --all-files --show-diff-on-failure', echo=True)


@task(aliases=['req'])
def requirements(ctx, base=False, addons=False, release=False, dev=False, all=False):
    """Install python dependencies.

    Examples:
        inv requirements
        inv requirements --all

    You should use --all for updating your developement environment.
    --all will install (in order): addons, dev and the base requirements.

    By default, base requirements will run. However, if any set of addons, release, or dev are chosen, base
    will have to be mentioned explicitly in order to run. This is to remain compatible with previous usages. Release
    requirements will prevent dev, and base from running.
    """
    if all:
        base = True
        addons = True
        dev = True
    if not(addons or dev):
        base = True
    if release or addons:
        addon_requirements(ctx)
    # "release" takes precedence
    if release:
        req_file = os.path.join(HERE, 'requirements', 'release.txt')
        ctx.run(
            pip_install(req_file),
            echo=True
        )
    else:
        if dev:  # then dev requirements
            req_file = os.path.join(HERE, 'requirements', 'dev.txt')
            ctx.run(
                pip_install(req_file),
                echo=True
            )

        if base:  # then base requirements
            req_file = os.path.join(HERE, 'requirements.txt')
            ctx.run(
                pip_install(req_file),
                echo=True
            )
    # fix URITemplate name conflict h/t @github
    ctx.run('pip3 uninstall uritemplate.py --yes || true')
    ctx.run('pip3 install --no-cache-dir uritemplate.py==0.3.0')


@task
def test_module(ctx, module=None, numprocesses=None, nocapture=False, params=None, coverage=False, testmon=False):
    """Helper for running tests.
    """
    from past.builtins import basestring
    os.environ['DJANGO_SETTINGS_MODULE'] = 'osf_tests.settings'
    import pytest
    if not numprocesses:
        from multiprocessing import cpu_count
        numprocesses = cpu_count()
    numprocesses = int(numprocesses)
    # NOTE: Subprocess to compensate for lack of thread safety in the httpretty module.
    # https://github.com/gabrielfalcao/HTTPretty/issues/209#issue-54090252
    args = []
    if coverage:
        args.extend([
            '--cov-report', 'term-missing',
            '--cov', 'admin',
            '--cov', 'addons',
            '--cov', 'api',
            '--cov', 'framework',
            '--cov', 'osf',
            '--cov', 'website',
        ])
    if not nocapture:
        args += ['-s']
    if numprocesses > 1:
        args += ['-n {}'.format(numprocesses), '--max-slave-restart=0']
    modules = [module] if isinstance(module, basestring) else module
    args.extend(modules)
    if testmon:
        args.extend(['--testmon'])

    if params:
        params = [params] if isinstance(params, basestring) else params
        args.extend(params)

    retcode = pytest.main(args)

    # exit code 5 is all tests skipped which is the same as passing with testmon
    sys.exit(0 if retcode == NO_TESTS_COLLECTED else retcode)


OSF_TESTS = [
    'osf_tests',
]

WEBSITE_TESTS = [
    'tests',
]

API_TESTS1 = [
    'api_tests/draft_registrations',
    'api_tests/draft_nodes',
    'api_tests/identifiers',
    'api_tests/institutions',
    'api_tests/licenses',
    'api_tests/logs',
    'api_tests/schemas',
    'api_tests/providers',
    'api_tests/preprints',
    'api_tests/registrations',
    'api_tests/users',
]
API_TESTS2 = [
    'api_tests/actions',
    'api_tests/chronos',
    'api_tests/meetings',
    'api_tests/metrics',
    'api_tests/nodes',
    'api_tests/osf_groups',
    'api_tests/requests',
    'api_tests/subscriptions',
    'api_tests/waffle',
    'api_tests/wb',
]
API_TESTS3 = [
    'api_tests/addons_tests',
    'api_tests/alerts',
    'api_tests/applications',
    'api_tests/banners',
    'api_tests/base',
    'api_tests/collections',
    'api_tests/comments',
    'api_tests/crossref',
    'api_tests/files',
    'api_tests/guids',
    'api_tests/reviews',
    'api_tests/regions',
    'api_tests/search',
    'api_tests/scopes',
    'api_tests/sloan',
    'api_tests/subjects',
    'api_tests/taxonomies',
    'api_tests/test',
    'api_tests/tokens',
    'api_tests/view_only_links',
    'api_tests/wikis',
]
ADDON_TESTS = [
    'addons',
]
ADMIN_TESTS = [
    'admin_tests',
]


@task
def test_osf(ctx, numprocesses=None, coverage=False, testmon=False):
    """Run the GakuNin RDM test suite."""
    print('Testing modules "{}"'.format(OSF_TESTS))
    test_module(ctx, module=OSF_TESTS, numprocesses=numprocesses, coverage=coverage, testmon=testmon)

@task
def test_website(ctx, numprocesses=None, coverage=False, testmon=False):
    """Run the old test suite."""
    print('Testing modules "{}"'.format(WEBSITE_TESTS))
    test_module(ctx, module=WEBSITE_TESTS, numprocesses=numprocesses, coverage=coverage, testmon=testmon)

@task
def test_api1(ctx, numprocesses=None, coverage=False, testmon=False):
    """Run the API test suite."""
    print('Testing modules "{}"'.format(API_TESTS1 + ADMIN_TESTS))
    test_module(ctx, module=API_TESTS1 + ADMIN_TESTS, numprocesses=numprocesses, coverage=coverage, testmon=testmon)


@task
def test_api2(ctx, numprocesses=None, coverage=False, testmon=False):
    """Run the API test suite."""
    print('Testing modules "{}"'.format(API_TESTS2))
    test_module(ctx, module=API_TESTS2, numprocesses=numprocesses, coverage=coverage, testmon=testmon)


@task
def test_api3(ctx, numprocesses=None, coverage=False, testmon=False):
    """Run the API test suite."""
    print('Testing modules "{}"'.format(API_TESTS3 + OSF_TESTS))
    # NOTE: There may be some concurrency issues with ES
    test_module(ctx, module=API_TESTS3 + OSF_TESTS, numprocesses=numprocesses, coverage=coverage, testmon=testmon)


@task
def test_admin(ctx, numprocesses=None, coverage=False, testmon=False):
    """Run the Admin test suite."""
    print('Testing module "admin_tests"')
    test_module(ctx, module=ADMIN_TESTS, numprocesses=numprocesses, coverage=coverage, testmon=testmon)


@task
def test_addons(ctx, numprocesses=None, coverage=False, testmon=False):
    """Run all the tests in the addons directory.
    """
    print('Testing modules "{}"'.format(ADDON_TESTS))
    test_module(ctx, module=ADDON_TESTS, numprocesses=numprocesses, coverage=coverage, testmon=testmon)


@task
def test(ctx, all=False, lint=False):
    """
    Run unit tests: OSF (always), plus addons and syntax checks (optional)
    """
    if lint:
        syntax(ctx)

    test_website(ctx)  # /tests
    test_api1(ctx)
    test_api2(ctx)
    test_api3(ctx)  # also /osf_tests

    if all:
        test_addons(ctx)
        # TODO: Enable admin tests
        test_admin(ctx)
        karma(ctx)

@task
def remove_failures_from_testmon(ctx, db_path=None):

    conn = sqlite3.connect(db_path)
    try:
        tests_decached = conn.execute("delete from node where result <> '{}'").rowcount
    except Exception:
        # Typically "sqlite3.OperationalError: no such table: node"
        tests_decached = 0
    ctx.run('echo {} failures purged from travis cache'.format(tests_decached))

@task
def travis_setup(ctx):
    ctx.run('npm install -g bower', echo=True)

    with open('package.json', 'r') as fobj:
        package_json = json.load(fobj)
        ctx.run('npm install @centerforopenscience/list-of-licenses@{}'.format(package_json['dependencies']['@centerforopenscience/list-of-licenses']), echo=True)

    with open('bower.json', 'r') as fobj:
        bower_json = json.load(fobj)
        ctx.run('bower install {}'.format(bower_json['dependencies']['styles']), echo=True)

@task
def test_travis_addons(ctx, numprocesses=None, coverage=False, testmon=False):
    """
    Run half of the tests to help travis go faster.
    """
    travis_setup(ctx)
    syntax(ctx)
    test_addons(ctx, numprocesses=numprocesses, coverage=coverage, testmon=testmon)

@task
def test_travis_website(ctx, numprocesses=None, coverage=False, testmon=False):
    """
    Run other half of the tests to help travis go faster.
    """
    travis_setup(ctx)
    test_website(ctx, numprocesses=numprocesses, coverage=coverage, testmon=testmon)


@task
def test_travis_api1_and_js(ctx, numprocesses=None, coverage=False, testmon=False):
    # TODO: Uncomment when https://github.com/travis-ci/travis-ci/issues/8836 is resolved
    # karma(ctx)
    travis_setup(ctx)
    test_api1(ctx, numprocesses=numprocesses, coverage=coverage, testmon=testmon)


@task
def test_travis_api2(ctx, numprocesses=None, coverage=False, testmon=False):
    travis_setup(ctx)
    test_api2(ctx, numprocesses=numprocesses, coverage=coverage, testmon=testmon)


@task
def test_travis_api3_and_osf(ctx, numprocesses=None, coverage=False, testmon=False):
    travis_setup(ctx)
    test_api3(ctx, numprocesses=numprocesses, coverage=coverage, testmon=testmon)

@task
def karma(ctx, travis=False):
    """Run JS tests with Karma. Requires Chrome to be installed."""
    if travis:
        return ctx.run('yarn test-travis', echo=True)
    ctx.run('yarn test', echo=True)


@task
def wheelhouse(ctx, addons=False, release=False, dev=False, pty=True):
    """Build wheels for python dependencies.

    Examples:

        inv wheelhouse --dev
        inv wheelhouse --addons
        inv wheelhouse --release
    """
    if release or addons:
        for directory in os.listdir(settings.ADDON_PATH):
            path = os.path.join(settings.ADDON_PATH, directory)
            if os.path.isdir(path):
                req_file = os.path.join(path, 'requirements.txt')
                if os.path.exists(req_file):
                    cmd = ('pip3 wheel --find-links={} -r {} --wheel-dir={} ').format(WHEELHOUSE_PATH, req_file, WHEELHOUSE_PATH)
                    ctx.run(cmd, pty=pty)
    if release:
        req_file = os.path.join(HERE, 'requirements', 'release.txt')
    elif dev:
        req_file = os.path.join(HERE, 'requirements', 'dev.txt')
    else:
        req_file = os.path.join(HERE, 'requirements.txt')
    cmd = 'pip3 wheel --find-links={} -r {} --wheel-dir={} '.format(WHEELHOUSE_PATH, req_file, WHEELHOUSE_PATH)
    ctx.run(cmd, pty=pty)


@task
def addon_requirements(ctx):
    """Install all addon requirements."""
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory)

        requirements_file = os.path.join(path, 'requirements.txt')
        if os.path.isdir(path) and os.path.isfile(requirements_file):
            print('Installing requirements for {0}'.format(directory))
            ctx.run(
                pip_install(requirements_file),
                echo=True
            )

    print('Finished installing addon requirements')


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


@task(aliases=['bower'])
def bower_install(ctx):
    print('Installing bower-managed packages')
    bower_bin = os.path.join(HERE, 'node_modules', '.bin', 'bower')
    ctx.run('{} prune --allow-root'.format(bower_bin), echo=True)
    ctx.run('{} install --allow-root'.format(bower_bin), echo=True)


@task
def docker_init(ctx):
    """Initial docker setup"""
    print('You will be asked for your sudo password to continue...')
    if platform.system() == 'Darwin':  # Mac OSX
        ctx.run('sudo ifconfig lo0 alias 192.168.168.167')
    else:
        print('Your system is not recognized, you will have to setup docker manually')

def ensure_docker_env_setup(ctx):
    if hasattr(os.environ, 'DOCKER_ENV_SETUP') and os.environ['DOCKER_ENV_SETUP'] == '1':
        pass
    else:
        os.environ['WEB_REMOTE_DEBUG'] = '192.168.168.167:11000'
        os.environ['API_REMOTE_DEBUG'] = '192.168.168.167:12000'
        os.environ['WORKER_REMOTE_DEBUG'] = '192.168.168.167:13000'
        os.environ['DOCKER_ENV_SETUP'] = '1'
        docker_init(ctx)

@task
def docker_requirements(ctx):
    ensure_docker_env_setup(ctx)
    ctx.run('docker-compose up requirements requirements_mfr requirements_wb')

@task
def docker_appservices(ctx):
    ensure_docker_env_setup(ctx)
    ctx.run('docker-compose up assets fakecas elasticsearch tokumx postgres')

@task
def docker_osf(ctx):
    ensure_docker_env_setup(ctx)
    ctx.run('docker-compose up mfr wb web api')

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
        ctx.run('git push --follow-tags origin master', echo=True)
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
    args = ['yarn run webpack-{}'.format('dev' if dev else 'prod')]
    args += ['--progress']
    if watch:
        args += ['--watch']
    if colors:
        args += ['--colors']
    command = ' '.join(args)
    ctx.run(command, echo=True)


@task()
def build_js_config_files(ctx):
    from website import settings
    print('Building JS config files...')
    with open(os.path.join(settings.STATIC_FOLDER, 'built', 'nodeCategories.json'), 'w') as fp:
        json.dump(settings.NODE_CATEGORY_MAP, fp)
    print('...Done.')


@task()
def assets(ctx, dev=False, watch=False, colors=False):
    """Install and build static assets."""
    command = 'yarn install --frozen-lockfile'
    if not dev:
        command += ' --production'
    ctx.run(command, echo=True)
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
def set_maintenance(ctx, message='', level=1, start=None, end=None):
    from website.app import setup_django
    setup_django()
    from website.maintenance import set_maintenance
    """Display maintenance notice across OSF applications (incl. preprints, registries, etc.)

    start - Start time for the maintenance period
    end - End time for the mainteance period
        NOTE: If no start or end values are provided, default to starting now
        and ending 24 hours from now.
    message - Message to display. If omitted, will be:
        "The site will undergo maintenance between <localized start time> and <localized end time>. Thank you
        for your patience."
    level - Severity level. Modifies the color of the displayed notice. Must be one of 1 (info), 2 (warning), 3 (danger).

    Examples:
        invoke set_maintenance --start 2016-03-16T15:41:00-04:00 --end 2016-03-16T15:42:00-04:00
        invoke set_maintenance --message 'The OSF is experiencing issues connecting to a 3rd party service' --level 2 --start 2016-03-16T15:41:00-04:00 --end 2016-03-16T15:42:00-04:00
    """
    state = set_maintenance(message, level, start, end)
    print('Maintenance notice up {} to {}.'.format(state['start'], state['end']))


@task
def unset_maintenance(ctx):
    from website.app import setup_django
    setup_django()
    from website.maintenance import unset_maintenance
    print('Taking down maintenance notice...')
    unset_maintenance()
    print('...Done.')


@task
def mapcore_config(ctx, sync=None):
    '''mAP core configurations

    Examples:
        inv mapcore_config --sync=yes
        inv mapcore_config --sync=no
    '''
    from website.app import init_app
    init_app(routes=False)

    from nii.mapcore import (mapcore_sync_is_enabled,
                             mapcore_sync_set_enabled,
                             mapcore_sync_set_disabled)

    def bool_from_str(name, s):
        if s.lower() in ['enable', 'true', 'yes', 'on', '1']:
            return True
        if s.lower() in ['disable', 'false', 'no', 'off', '0']:
            return False
        raise Exception('--{} expects yes or no: {}'.format(name, s))

    if sync is not None:
        if bool_from_str('sync', sync):
            mapcore_sync_set_enabled()
        else:
            mapcore_sync_set_disabled()

    print('mapcore_sync_is_enabled: {}'.format(mapcore_sync_is_enabled()))


@task
def mapcore_upload_all(ctx):
    '''Synchronize all GRDM projects to mAP core'''
    from website.app import init_app
    init_app(routes=False)

    from nii.mapcore import (mapcore_disable_log,
                             mapcore_sync_is_enabled,
                             mapcore_sync_upload_all)

    mapcore_disable_log(level=logging.ERROR)
    if mapcore_sync_is_enabled():
        count_all_nodes, error_nodes = mapcore_sync_upload_all()
        idx = 0
        for error_node in error_nodes:
            idx += 1
            print('error node {}: guid={}'.format(idx, error_node._id))
        count_error_nodes = len(error_nodes)
        print('count_error_nodes={}'.format(count_error_nodes))
        print('count_all_nodes={}'.format(count_all_nodes))
        if count_error_nodes > 0:
            sys.exit(1)
    else:
        print('mapcore_sync_is_enabled: False')
        sys.exit(1)

@task
def mapcore_remove_token(ctx, username=None, eppn=None):
    '''Remove OAuth token for mAP core'''
    from website.app import init_app
    init_app(routes=False)

    from osf.models import OSFUser
    from nii.mapcore import mapcore_remove_token

    user = None
    if username:
        try:
            user = OSFUser.objects.get(username=username)
        except Exception as e:
            print(e)
            print('Error: no such username: ' + username)
            print('--- existing username list ---')
            for user in OSFUser.objects.all():
                print(user.username)
            return
    elif eppn:
        try:
            user = OSFUser.objects.get(eppn=eppn)
        except Exception as e:
            print(e)
            print('Error: no such ePPN: ' + eppn)
            print('--- existing ePPN list ---')
            for user in OSFUser.objects.all():
                if user.eppn:
                    print(user.eppn)
            return
    else:
        ctx.run('invoke --help mapcore_remove_token')
        return
    mapcore_remove_token(user)
    if username:
        print('token is REMOVED: username = ' + user.username)
    elif eppn:
        print('token is REMOVED: ePPN = ' + user.eppn)


@task(help={'user': 'filter with creator\'s mail address',
            'file': 'file name contains group_key list',
            'grdm': 'remove groups from GRDM',
            'map': 'remove groups from mAP',
            'key-only': 'remove link (group_key) only',
            'interactive': 'select delete groups interactively',
            'verbose': 'show more group information',
            'dry-run': 'dry-run'})
def mapcore_rmgroups(ctx, user=None, file=None, grdm=False, map=False, key_only=False,
                     interactive=False, verbose=False, dry_run=False):
    '''GRDM/mAP group maintanance utility for bulk deletion'''
    from website.app import init_app
    init_app(routes=False)

    from nii.rmgroups import Options, remove_multi_groups

    options = Options(user, file, grdm, map, key_only, interactive, verbose, dry_run)
    remove_multi_groups(options)


@task
def mapcore_unlock_all(ctx):
    '''Remove all lock flags for mAP core'''
    from website.app import init_app
    init_app(routes=False)

    from nii import mapcore
    mapcore.mapcore_unlock_all()


@task
def mapcore_test_lock(ctx):
    '''test lock functions for mapcore.py'''
    from multiprocessing import Process
    from website.app import init_app
    import time

    sleep_sec = 5
    n_proc = 3

    def test_lock_user(idx):
        print('start: test_lock_user[{}]'.format(idx))
        init_app(routes=False)
        from nii.mapcore import user_lock_test
        from osf.models import OSFUser

        u = OSFUser.objects.order_by('id').first()
        user_lock_test(u, sleep_sec)

    def test_lock_node(idx):
        print('start: test_lock_node[{}]'.format(idx))
        init_app(routes=False)
        from nii.mapcore import node_lock_test
        from osf.models import Node

        n = Node.objects.order_by('id').first()
        node_lock_test(n, sleep_sec)

    def test_base(func, name):
        procs = []
        for i in range(n_proc):
            p = Process(target=func, args=(i,))
            procs.append(p)

        t1 = time.time()
        for p in procs:
            p.start()
        for p in procs:
            p.join()
        t2 = time.time()
        print('total time: {} sec.'.format(t2 - t1))
        if ((t2 - t1) >= sleep_sec * n_proc):
            print('*** OK: ' + name)
            return True
        else:
            print('*** NG: ' + name)
            return False

    r1 = test_base(test_lock_user, 'test lock user')
    r2 = test_base(test_lock_node, 'test lock node')

    if not (r1 and r2):
        print('ERROR: mapcore_test_lock')
