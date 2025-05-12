# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import time
import inspect
import functools
from unicodedata import normalize
from pprint import pformat as pp

import mock
import pytest
from nose.tools import *  # noqa: F403

from framework.auth.core import Auth
from osf_tests import factories
from osf_tests.test_elastic_search import retry_assertion
from api_tests import utils as api_utils
from tests.base import OsfTestCase
from tests.utils import run_celery_tasks

from osf.models import Guid, Comment
from website import settings
from website.util import web_url_for, api_url_for
from website.views import find_bookmark_collection
import website.search.search as search
from addons.wiki.models import WikiPage
from addons.osfstorage import settings as osfstorage_settings
from addons.osfstorage.models import OsfStorageFileNode

from website.search.util import (quote_query_string, convert_query_string,
                                 NORMALIZED_FIELDS)
from website.search_migration.migrate import migrate

ENABLE_DEBUG = False

def build_query(query_string):
    return {
        'query': {
            'filtered': {
                'query': {
                    'query_string': {
                        'default_field': '_all',
                        'fields': [
                            '_all',
                            'title^4',
                            'description^1.2',
                            'job^1',
                            'school^1',
                            'all_jobs^0.125',
                            'all_schools^0.125'
                        ],
                        'query': query_string,
                        'analyze_wildcard': True,
                        'lenient': True
                    }
                }
            }
        },
        'from': 0,
        'size': 100
    }

HIGHLIGHT_SIZE_TITLE = 30
HIGHLIGHT_SIZE_TEXT = 124

def build_private_search_query(query_string, version=1, sort=None, highlight=None):
    q = {
        'api_version': {
            'version': version,
            'vendor': 'grdm'
        },
        'elasticsearch_dsl': build_query(query_string)
    }
    if sort:
        q['sort'] = sort
    if highlight is None:
        q['highlight'] = 'title:{},name:{},user:{},text:{},comments.*:{}'.format(HIGHLIGHT_SIZE_TITLE, HIGHLIGHT_SIZE_TITLE, HIGHLIGHT_SIZE_TITLE, HIGHLIGHT_SIZE_TEXT, HIGHLIGHT_SIZE_TEXT)

    DEBUG('build_private_search_query', q)
    return q


def DEBUG(msg, obj=None):
    if ENABLE_DEBUG:
        if obj:
            print('{}:\n{}'.format(msg, se(u2s(obj))), file=sys.stderr)
        else:
            print(msg, file=sys.stderr)

# FIXME: use Unicode in Python3
def s2u(obj):
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    if isinstance(obj, list):
        return [s2u(s) for s in obj]
    if isinstance(obj, dict):
        return {s2u(key): s2u(val) for key, val in obj.iteritems()}
    return obj

def u2s(obj):
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return [u2s(s) for s in obj]
    if isinstance(obj, dict):
        return {u2s(key): u2s(val) for key, val in obj.iteritems()}
    return obj

# string-escape
def se(listordict):
    return pp(listordict).decode('string-escape')

def get_contributors(results, node_title):
    node_title = s2u(node_title)
    for result in results:
        if result['category'] != 'project':
            continue
        if s2u(result['title']) == node_title:
            return [c['fullname'] for c in result['contributors']]
    return []

def get_tags(results, node_title):
    node_title = s2u(node_title)
    for result in results:
        if result['category'] != 'project':
            continue
        if s2u(result['title']) == node_title:
            return [r for r in result['tags']]
    return []

def get_filetags(results, file_name):
    file_name = s2u(file_name)
    for result in results:
        if result['category'] != 'file':
            continue
        if s2u(result['name']) == file_name:
            return [r for r in result['tags']]
    return []

def get_user_fullnames(results):
    return [r['names']['fullname'] for r in results if r['category'] == 'user']

def get_filenames(results):
    return [r['name'] for r in results if r['category'] == 'file']

def get_node_titles(results):
    return [r['title'] for r in results if r['category'] in
            ['project', 'component', 'registration', 'preprint']]

def get_category_count_map(results):
    rv = {}
    for result in results:
        category = result['category']
        if category in rv:
            rv[category] += 1
        else:
            rv[category] = 1
    return rv

def enable_private_search(func):
    @mock.patch('website.search_migration.migrate.settings.ENABLE_PRIVATE_SEARCH', True)
    @mock.patch('website.search.views.settings.ENABLE_PRIVATE_SEARCH', True)
    @mock.patch('website.search.elastic_search.settings.ENABLE_PRIVATE_SEARCH', True)
    @mock.patch('website.search.elastic_search.settings.ENABLE_MULTILINGUAL_SEARCH', True)
    @mock.patch('website.search.util.settings.ENABLE_MULTILINGUAL_SEARCH', True)
    @mock.patch('website.project.tasks.settings.ENABLE_PRIVATE_SEARCH', True)
    @mock.patch('website.routes.settings.ENABLE_PRIVATE_SEARCH', True)
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapped

def use_ja_analyzer(func):
    @mock.patch('website.search.elastic_search.settings.SEARCH_ANALYZER',
                settings.SEARCH_ANALYZER_JAPANESE)
    @mock.patch('website.search.util.settings.SEARCH_ANALYZER',
                settings.SEARCH_ANALYZER_JAPANESE)
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapped

def setup(cls, self, create_obj=True):
    super(cls, self).setUp()
    search.delete_all()
    search.create_index(None)
    if not create_obj:
        return

    with run_celery_tasks():
        self.user1 = factories.AuthUserFactory(fullname='日本語ユーザー1')
        self.user2 = factories.AuthUserFactory(fullname='日本語ユーザー2')
        self.user3 = factories.AuthUserFactory(
            fullname=u'\u304b\u3099')  # か+濁点
        self.user4 = factories.AuthUserFactory(
            fullname=u'\u304e')  # ぎ
        self.user5 = factories.AuthUserFactory(
            fullname=u'\u306f\u3099')  # は+濁点
        self.user6 = factories.AuthUserFactory(
            fullname=u'\u3073')  # び

        self.project_private_user1_1 = factories.ProjectFactory(
            title='private日本語プロジェクト1_1',
            creator=self.user1,
            description=u'\u304f\u3099',  # く+濁点
            is_public=False)
        rootdir = self.project_private_user1_1.get_addon('osfstorage').get_root()
        self.f1 = rootdir.append_file(u'日本語ファイル名.txt')
        self.f1.add_tag('12345',
                        Auth(self.user1), save=False)
        self.f1.add_tag(u'\uff16\uff17\uff18\uff19\uff10',  # ６７８９０
                        Auth(self.user1), save=False)
        self.f1.save()
        self.f2 = rootdir.append_file(u'\u305f\u3099')  # た+濁点
        self.f3 = rootdir.append_file(u'\u3062')  # ぢ
        self.project_private_user1_1.add_tag(u'日本語タグ',
                                             Auth(self.user1),
                                             save=False)
        self.project_private_user1_1.add_tag(u'\u3064\u3099',  # つ+濁点
                                             Auth(self.user1),
                                             save=False)
        self.project_private_user1_1.add_tag(u'\u3067',  # で
                                             Auth(self.user1),
                                             save=False)
        self.project_private_user1_1.save()
        self.wiki1 = WikiPage.objects.create_for_node(
            self.project_private_user1_1,
            u'\u3055\u3099',  # page name (wiki_names:): さ+濁点
            u'\u3059\u3099',  # content (wikis:): す+濁点
            Auth(self.user1))
        self.wiki2 = WikiPage.objects.create_for_node(
            self.project_private_user1_1,
            u'\u3058',  # page name (wiki_names:): じ
            u'\u305c',  # content (wikis:): ぜ
            Auth(self.user1))

        self.project_private_user1_2 = factories.ProjectFactory(
            title='private日本語プロジェクト1_2',
            creator=self.user1,
            description=u'\u3052',  # げ
            is_public=False)

        self.project_private_user2_1 = factories.ProjectFactory(
            title='private日本語プロジェクト2_1',
            creator=self.user2,
            is_public=False)
        self.project_private_user2_2 = factories.ProjectFactory(
            title='private日本語プロジェクト2_2',
            creator=self.user2,
            is_public=False)

        self.project_private_user3 = factories.ProjectFactory(
            title=u'private日本語プロジェクト3 \u3054',  # ご
            creator=self.user3,
            is_public=False)
        self.project_private_user3.add_contributor(
            self.user5, auth=Auth(self.user3))
        # tagged by user5
        self.project_private_user3.add_tag(u'tag_for_private_project_3',
                                           Auth(self.user5),
                                           save=False)

        self.project_private_user4 = factories.ProjectFactory(
            title=u'private日本語プロジェクト4 \u305d\u3099',  # そ+濁点
            creator=self.user4,
            is_public=False)
        self.project_private_user4.add_contributor(
            self.user6, auth=Auth(self.user4))
        # tagged by user6
        self.project_private_user4.add_tag(u'tag_for_private_project_4',
                                           Auth(self.user6),
                                           save=False)

        self.project_public_user1 = factories.ProjectFactory(
            title='public日本語プロジェクト1',
            creator=self.user1,
            is_public=True)
        self.project_public_user2 = factories.ProjectFactory(
            title='public日本語プロジェクト2',
            creator=self.user2,
            is_public=True)

def tear_down(cls, self):
    super(cls, self).tearDown()
    import website.search.search as search
    search.delete_all()

def query_private_search(self, qs, user, category=None, version=1, sort=None):
    url = api_url_for('search_search')
    if category:
        url = url + category + '/'
    DEBUG('query_private_search: url=', url)
    res = self.app.post_json(
        url,
        build_private_search_query(qs, version=version, sort=sort),
        auth=user.auth,
        expect_errors=True
    )
    DEBUG('query_private_search: res=', res.json)
    return res, res.json.get('results')

def query_public_search(self, qs, user):
    res = self.app.post_json(
        api_url_for('search_search'),
        build_query(qs),
        auth=user.auth,
        expect_errors=True
    )
    return res, res.json.get('results')

def query_search_contributor(self, qs, user):
    res = self.app.get(
        api_url_for('search_contributor'),
        {'query': qs, 'page': 0, 'size': 100},
        auth=user.auth,
        expect_errors=True
    )
    DEBUG('query_search_contributor', res)
    return res, res.json.get('users')

def query_for_normalize_tests(self, qs, category=None, user=None, version=1):
    if user is None:
        user = self.user1
    # app.get() requires str
    qs = u2s(qs)
    res, results = query_private_search(self, qs, user, category=category,
                                        version=version)
    return (res, results)

def update_dummy_file(user, dir_node, name, version):
    try:
        test_file = dir_node.find_child_by_name(name)
    except OsfStorageFileNode.DoesNotExist:
        test_file = None
    if test_file is None:
        test_file = dir_node.append_file(name)

    test_file.create_version(user, {
        # NOTE: Same object as latest does not update FileVersion
        'object': '06d80e' + str(version),
        'service': 'cloud',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': 1337 + version,
        'contentType': 'img/png'
    }).save()
    return test_file

def nfc(text):
    return normalize('NFC', text)

def nfd(text):
    return normalize('NFD', text)

@retry_assertion(retries=10)
def retry_call_func(func, **kwargs):
    func(**kwargs)

@enable_private_search
def rebuild_search(self_):
    migrate(delete=False, remove=True,
            index=None, app=self_.app.app)

def run_after_rebuild_search(self_, func, **kwargs):
    # _use_migrate = False の場合は rebuild_search を実行しない。
    if not hasattr(self_, '_use_migrate') or self_._use_migrate:
        rebuild_search(self_)
        # migrate() may not update elasticsearch-data immediately.
        retry_call_func(func, **kwargs)
    else:
        func(**kwargs)

@enable_private_search
def run_test_all_after_rebuild_search(self_, my_method_name, clear_index=False):
    self_._use_migrate = True
    rebuild_search(self_)

    EXCLUDES = (my_method_name,
                'test_search_not_allowed',)
    for method_info in inspect.getmembers(self_, inspect.ismethod):
        method_name = method_info[0]
        DEBUG('*** method_name ***', '{}'.format(method_name))
        if method_name.startswith('test_') and \
           not method_name in EXCLUDES:
            # print('*** after rebuild_search: {}'.format(method_name), file=sys.stderr)
            if clear_index:
                search.delete_all()
                search.create_index(None)
            # migrate() may not update elasticsearch-data immediately.
            retry_call_func(getattr(self_, method_name))
        # テスト中に run_after_rebuild_search を呼ぶ場合があるので、
        # rebuild_search 呼び出し回数を上記 1 回だけにする。
        self_._use_migrate = False


###### tests #####

@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchJapanese(OsfTestCase):
    """
    SEARCH_ANALYZER_JAPANESEを使う場合のテスト
    """

    @enable_private_search
    @use_ja_analyzer
    def setUp(self):
        setup(TestSearchJapanese, self, create_obj=False)

    @enable_private_search
    @use_ja_analyzer
    def tearDown(self):
        tear_down(TestSearchJapanese, self)

    @enable_private_search
    @use_ja_analyzer
    def test_normalize_all(self):
        """
        Unicode正規化のテスト。
        結合文字<->合成済み文字 の相互検索できることを確認する。
        rebuild_search相当実行後も検索できることを確認する。
        各フィールドごとに検索できることを確認する。
        削除して影響ないことを確認する。
        """
        nfd_str = nfd(u'ギガバイト')  # 結合文字
        nfc_str = nfc(nfd_str)  # 合成済み文字
        search_user = factories.AuthUserFactory()

        def _save_username(val):
            user = factories.AuthUserFactory(fullname=val)
            return user

        def _set_job(inst, depart, title, ongoing):
            return {
                'institution': inst,
                'department': depart,
                'title': title,
                'ongoing': ongoing,
            }

        def _save_ongoing_job_institution(val):
            user = factories.AuthUserFactory()
            user.jobs = []
            user.jobs.append(_set_job(val, None, None, True))
            user.save()
            return user

        def _save_ongoing_job_department(val):
            user = factories.AuthUserFactory()
            user.jobs = []
            user.jobs.append(_set_job(None, val, None, True))
            user.save()
            return user

        def _save_ongoing_job_title(val):
            user = factories.AuthUserFactory()
            user.jobs = []
            user.jobs.append(_set_job(None, None, val, True))
            user.save()
            return user

        def _set_school(inst, depart, degree, ongoing):
            return {
                'institution': inst,
                'department':depart,
                'degree': degree,
                'ongoing': ongoing,
            }

        def _save_ongoing_school_institution(val):
            user = factories.AuthUserFactory()
            user.schools = []
            user.schools.append(_set_school(val, None, None, True))
            user.save()
            return user

        def _save_ongoing_school_department(val):
            user = factories.AuthUserFactory()
            user.schools = []
            user.schools.append(_set_school(None, val, None, True))
            user.save()
            return user

        def _save_ongoing_school_degree(val):
            user = factories.AuthUserFactory()
            user.schools = []
            user.schools.append(_set_school(None, None, val, True))
            user.save()
            return user

        def _del_user(user):
            user.gdpr_delete()
            user.save()

        def _save_project_title(val):
            project = factories.ProjectFactory(
                title=val, creator=search_user, is_public=False)
            project.save()
            return project

        def _save_project_description(val):
            project = factories.ProjectFactory(
                description=val, creator=search_user, is_public=False)
            project.save()
            return project

        def _save_project_comment(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            c_old = factories.CommentFactory(
                node=project, user=search_user, page=Comment.OVERVIEW,
                content=val)
            project.save()
            return project

        def _save_project_tag(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            project.add_tag(val, Auth(search_user), save=True)
            return project

        def _save_project_contributor(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            user1 = factories.AuthUserFactory(fullname=val)
            project.add_contributor(
                user1, auth=Auth(search_user))
            return (project, user1)

        def _save_project_creator(val):
            user1 = factories.AuthUserFactory(fullname=val)
            project = factories.ProjectFactory(
                creator=user1, is_public=False)
            project.add_contributor(
                search_user, auth=Auth(user1))
            return (project, user1)

        def _save_project_modifier(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            user1 = factories.AuthUserFactory(fullname=val)
            project.add_contributor(
                user1, auth=Auth(search_user))
            project.add_tag('dummy_tag_name', Auth(user1), save=True)
            return (project, user1)

        def _del_project(project):
            project.remove_node(auth=Auth(project.creator))
            # Do not call project.save()

        def _del_project2(project_user):
            project = project_user[0]
            user = project_user[1]
            _del_project(project)
            _del_user(user)

        def _update_file(filename, project, user, count):
            osfstorage = project.get_addon('osfstorage')
            root_node = osfstorage.get_root()
            test_file = update_dummy_file(user, root_node, filename, count)
            assert_equal(test_file.versions.count(), count)
            # first() of file.versions is latest
            assert_equal(test_file.versions.all().first().creator, user)
            return test_file

        def _save_file_name(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            _update_file(val, project, search_user, 1)
            return project

        def _save_file_comment(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            file1 = _update_file('dummy_filename', project, search_user, 1)
            comment = factories.CommentFactory(
                node=project, user=search_user, page=Comment.FILES,
                target=file1.get_guid(create=True),
                content=val)
            return project

        def _save_file_tag(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            file1 = _update_file('dummy_filename', project, search_user, 1)
            file1.add_tag(val, Auth(search_user), save=True)
            return project

        def _save_file_creator(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            user1 = factories.AuthUserFactory(fullname=val)
            project.add_contributor(
                user1, auth=Auth(search_user))
            _update_file('dummy_filename', project, user1, 1)
            return (project, user1)

        def _save_file_modifier(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            user1 = factories.AuthUserFactory(fullname=val)
            project.add_contributor(
                user1, auth=Auth(search_user))
            _update_file('dummy_filename', project, search_user, 1)
            _update_file('dummy_filename', project, user1, 2)
            return (project, user1)

        def _update_wiki(wikiname, content, project, user, count):
            wiki = WikiPage.objects.get_for_node(project, wikiname)
            if wiki:
                wiki.update(user, content)
            else:
                wiki = WikiPage.objects.create_for_node(
                    project, wikiname, content, Auth(user))
            assert_equal(wiki.versions.count(), count)
            # latest
            assert_equal(wiki.get_versions().first().user, user)
            return wiki

        def _save_wiki_name(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            _update_wiki(val, 'dummy_content', project, search_user, 1)
            return project

        def _save_wiki_content(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            _update_wiki('dummy_wikiname', val, project, search_user, 1)
            return project

        def _save_wiki_comment(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            wiki1 = _update_wiki('dummy_wikiname', 'dummy_content',
                                 project, search_user, 1)
            comment = factories.CommentFactory(
                node=project, user=search_user, page=Comment.WIKI,
                target=Guid.load(wiki1._id), content=val)
            return project

        def _save_wiki_creator(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            user1 = factories.AuthUserFactory(fullname=val)
            project.add_contributor(user1, auth=Auth(search_user))
            _update_wiki('dummy_wikiname', 'dummy_content',
                         project, user1, 1)
            return (project, user1)

        def _save_wiki_modifier(val):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            user1 = factories.AuthUserFactory(fullname=val)
            project.add_contributor(user1, auth=Auth(search_user))
            _update_wiki('dummy_wikiname', 'dummy_content1',
                         project, search_user, 1)
            _update_wiki('dummy_wikiname', 'dummy_content2',
                         project, user1, 2)
            return (project, user1)

        def _save_institution_name(val):
            inst = factories.InstitutionFactory(name=val)
            return inst

        def _del_institution(inst):
            inst.is_deleted = True
            inst.save()

        def _search(_id, qs):
            res, results = query_for_normalize_tests(
                self, u'{}'.format(qs), user=search_user, version=2)
            DEBUG('results()', results)
            try:
                assert_equal(len(results), 1)
            except Exception:
                DEBUG('test ID={}: error'.format(_id))
                raise

        patterns = (
            # user
            (1, _save_username, _del_user, None),
            (2, _save_ongoing_job_institution, _del_user, None),
            (3, _save_ongoing_job_department, _del_user, None),
            (4, _save_ongoing_job_title, _del_user, None),
            (5, _save_ongoing_school_institution, _del_user, None),
            (6, _save_ongoing_school_department, _del_user, None),
            (7, _save_ongoing_school_degree, _del_user, None),

            # project
            (8, _save_project_title, _del_project, None),
            (9, _save_project_description, _del_project, None),
            (10, _save_project_comment, _del_project, None),
            (11, _save_project_tag, _del_project, None),
            (12, _save_project_contributor, _del_project2,
             u'{} AND category:project'),
            (13, _save_project_creator, _del_project2,
             u'{} AND category:project'),
            (14, _save_project_modifier, _del_project2,
             u'{} AND category:project'),

            # file
            (15, _save_file_name, _del_project,
             u'{} AND category:file'),
            (16, _save_file_comment, _del_project,
             u'{} AND category:file'),
            (17, _save_file_tag, _del_project,
             u'{} AND category:file'),
            (18, _save_file_creator, _del_project2,
             u'{} AND category:file'),
            (19, _save_file_modifier, _del_project2,
             u'{} AND category:file'),

            # wiki
            (20, _save_wiki_name, _del_project,
             u'{} AND category:wiki'),
            (21, _save_wiki_content, _del_project,
             u'{} AND category:wiki'),
            (22, _save_wiki_comment, _del_project,
             u'{} AND category:wiki'),
            (23, _save_wiki_creator, _del_project2,
             u'{} AND category:wiki'),
            (24, _save_wiki_modifier, _del_project2,
             u'{} AND category:wiki'),

            # institution
            (25, _save_institution_name, _del_institution, None),

            # 最後の削除処理が次の検索に影響しないことを確認
            (999, _save_username, _del_user, None),
        )

        for pattern in patterns:
            _id = pattern[0]
            save_func = pattern[1]
            del_func = pattern[2]
            qs_fmt = pattern[3]

            # 結合文字 を 合成済み文字 で検索
            i='{}(NFD->NFC)'.format(_id)
            with run_celery_tasks():
                obj = save_func(nfd_str)
            if qs_fmt:
                qs = qs_fmt.format(nfc_str)
            else:
                qs = nfc_str
            _search(_id=i, qs=qs)
            run_after_rebuild_search(
                self, _search,
                _id='{}(after rebuild_search)'.format(i),
                qs=qs)
            with run_celery_tasks():
                del_func(obj)

            # 合成済み文字 を 結合文字 で検索
            i='{}(NFC->NFD)'.format(_id)
            with run_celery_tasks():
                obj = save_func(nfc_str)
            if qs_fmt:
                qs = qs_fmt.format(nfd_str)
            else:
                qs = nfd_str
            _search(_id=i, qs=qs)
            run_after_rebuild_search(
                self, _search,
                _id='{}(after rebuild_search)'.format(i),
                qs=qs)
            with run_celery_tasks():
                del_func(obj)


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchBugfix(OsfTestCase):
    """
    GakuNin RDM 版にて改修した挙動を確認するテスト
    """

    @enable_private_search
    @use_ja_analyzer
    def setUp(self):
        setup(TestSearchBugfix, self, create_obj=False)

    @enable_private_search
    @use_ja_analyzer
    def tearDown(self):
        tear_down(TestSearchBugfix, self)

    def _search(self, _id, search_user, qs, num):
        # 検索結果が存在しないことを確認する場合は、数回試す。
        # そうしないと、rebuild_search 後に
        # しばらくしてから検索結果に出現する問題を見逃す。
        if num == 0:
            test_count = 3
        else:
            test_count = 1
        for i in range(test_count):
            DEBUG('test ID={}: test_count {}/{}'.format(
                _id, i+1, test_count))
            if i != 0:
                time.sleep(1)
            res, results = query_for_normalize_tests(
                self, u'{}'.format(qs), user=search_user, version=2)
            DEBUG('results', results)
            try:
                assert_equal(len(results), num)
            except Exception:
                DEBUG('test ID={}: error'.format(_id))
                raise

    @enable_private_search
    @use_ja_analyzer
    def test_ignore_folder(self):
        """
        osfstoragefile のみが検索対象であることが期待動作である。
        フォルダーが検索結果に現れないことを確認する。
        rebuild_search 相当を実行後も同様に確認する。

        オリジナル osf.io の実装では、Web UI 上でファイル登録時には
        osfstragefile のみの情報が Elasticsearch に格納されていたが、
        rebuild_search 実行後は osfstoragefile 以外のフォルダーや
        他アドオンのファイル情報 が Elasticsearch に格納されていた。
        [GRDM-14562-4,19845]
        """

        search_user = factories.AuthUserFactory()

        def _create_file(name):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            osfstorage = project.get_addon('osfstorage')
            root_node = osfstorage.get_root()
            test_file = root_node.append_file(name)
            return project

        def _create_folder(name):
            project = factories.ProjectFactory(
                creator=search_user, is_public=False)
            osfstorage = project.get_addon('osfstorage')
            root_node = osfstorage.get_root()
            test_folder = root_node.append_folder(name)
            return project

        def _del_project(project):
            project.remove_node(auth=Auth(project.creator))

        patterns = (
            (1, _create_file, _del_project, u'ファイル', 1),
            (2, _create_folder, _del_project, u'フォルダー', 0),
        )

        for pattern in patterns:
            i = pattern[0]
            save_func = pattern[1]
            del_func = pattern[2]
            name = pattern[3]
            num = pattern[4]

            with run_celery_tasks():
                obj = save_func(name)
            self._search(_id=i, search_user=search_user, qs=name, num=num)
            run_after_rebuild_search(
                self, self._search,
                _id='{}(after rebuild_search)'.format(i),
                search_user=search_user, qs=name, num=num)
            with run_celery_tasks():
                del_func(obj)

    @enable_private_search
    @use_ja_analyzer
    def test_update_contributors(self):
        """
        Contributors に追加されたユーザーがそのプロジェクトを検索できる
        ことを確認する。

        Contributors から削除されたユーザーがそのプロジェクトを検索でき
        なくなることを確認する。

        Contributors に所属していたユーザー自体が削除されたら、その
        プロジェクトの検索結果にそのユーザーが含まれなくなることを確認
        する。

        オリジナル osf.io の実装では Contributors を増減させた直後は
        プロジェクトの検索結果に反映されず、
        タイトルなどを更新すると検索結果に Contributors が反映された。
        GRDM 版では検索可能範囲のアクセスコントロールのために
        Conotributors を見ているため、修正した。
        [GRDM-14562-4,19891]
        """

        admin = factories.AuthUserFactory()
        user1 = factories.AuthUserFactory()
        user2 = factories.AuthUserFactory()

        def _create_project(name):
            project = factories.ProjectFactory(
                title=name,
                creator=admin, is_public=False)
            return project

        def _del_project(project):
            project.remove_node(auth=Auth(project.creator))

        def _search(_id, search_user, qs, num):
            self._search(_id=_id, search_user=search_user, qs=qs, num=num)
            run_after_rebuild_search(
                self, self._search,
                _id='{}(after rebuild_search)'.format(_id),
                search_user=search_user, qs=qs, num=num)

        name = u'プロジェクト'
        i = 1
        with run_celery_tasks():
            p = _create_project(name)

        _search(1, admin, name, 1)  # visible
        _search(2, user1, name, 0)  # invisible

        with run_celery_tasks():
            p.add_contributor(user1, auth=Auth(admin))
            p.add_contributor(user2, auth=Auth(admin))

        _search(3, user1, name, 1)

        with run_celery_tasks():
            p.remove_contributor(user1, auth=Auth(admin))

        _search(4, user1, name, 0)
        _search(5, admin, u'category:project AND contributors.id:{}'.format(user1._id), 0)
        _search(6, admin, u'category:project AND contributors.id:{}'.format(user2._id), 1)

        with run_celery_tasks():
            user2.gdpr_delete()  # include remove_contributor

        _search(7, user2, name, 0)
        _search(8, admin, u'category:project AND contributors.id:{}'.format(user2._id), 0)

        with run_celery_tasks():
            _del_project(p)

        _search(9, admin, name, 0)

    @enable_private_search
    @use_ja_analyzer
    def test_delete_component(self):
        """
        コンポーネントを削除すると検索結果から消えることを確認する。

        オリジナル osf.io の実装では、コンポーネントを削除したあとも、
        検索結果に残る。
        [GRDM-19998]
        """

        admin = factories.AuthUserFactory()

        def _create_project(project_name, component_name):
            project = factories.ProjectFactory(
                title=project_name,
                creator=admin, is_public=False)
            component = factories.NodeFactory(
                parent=project,
                description='',
                title=component_name,
                creator=admin,
                is_public=False
            )
            return project

        def _del_project(project):
            project.remove_node(auth=Auth(project.creator))

        def _search(_id, search_user, qs, num):
            self._search(_id=_id, search_user=search_user, qs=qs, num=num)
            run_after_rebuild_search(
                self, self._search,
                _id='{}(after rebuild_search)'.format(_id),
                search_user=search_user, qs=qs, num=num)

        project_name = u'プロジェクト'
        component_name = u'コンポーネント'
        i = 1
        with run_celery_tasks():
            p = _create_project(project_name, component_name)

        _search(1, admin, component_name, 1)

        with run_celery_tasks():
            # 親プロジェクトを削除すると、コンポーネントも削除される
            _del_project(p)

        _search(2, admin, component_name, 0)

    @enable_private_search
    @use_ja_analyzer
    def test_visible_contributor(self):
        """
        目録表示メンバー(Bibliographic Contributor)ではないメンバーは、
        そのプロジェクトを検索できるが、検索結果には含まれないことを
        確認する。

        オリジナル osf.io の実装では、visible を ON/OFF しても、即座に
        検索結果に反映されない。
        [GRDM-20003]
        """

        admin = factories.AuthUserFactory()
        user1 = factories.AuthUserFactory()

        def _create_project():
            project = factories.ProjectFactory(
                creator=admin, is_public=False)
            return project

        def _del_project(project):
            project.remove_node(auth=Auth(project.creator))

        def _search(_id, search_user, qs, num):
            self._search(_id=_id, search_user=search_user, qs=qs, num=num)
            run_after_rebuild_search(
                self, self._search,
                _id='{}(after rebuild_search)'.format(_id),
                search_user=search_user, qs=qs, num=num)

        i = 1
        with run_celery_tasks():
            p = _create_project()
            p.add_contributor(user1)
            p.set_visible(user1, False, save=True)

        qs_title = 'category:project AND title:"{}"'.format(p.title)
        qs_username = 'category:project AND contributors.id:"{}"'.format(user1._id)

        _search(1, user1, qs_title, 1)
        _search(2, user1, qs_username, 0)
        _search(3, admin, qs_username, 0)

        with run_celery_tasks():
            p.set_visible(user1, True, save=True)

        _search(4, user1, qs_title, 1)
        _search(5, user1, qs_username, 1)
        _search(6, admin, qs_username, 1)

        with run_celery_tasks():
            _del_project(p)

        _search(7, user1, qs_title, 0)
        _search(8, user1, qs_username, 0)
        _search(9, admin, qs_username, 0)


# see osf_tests/test_search_views.py
@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestPrivateSearch(OsfTestCase):

    @enable_private_search
    def setUp(self):
        setup(TestPrivateSearch, self)

    @enable_private_search
    def tearDown(self):
        tear_down(TestPrivateSearch, self)

    def test_search_not_allowed(self):
        """
        ENABLE_PRIVATE_SEARCH = False の場合には、
        ENABLE_PRIVATE_SEARCH = True の際に格納したデータにアクセス
        できず、検索できないことを確認する。

        """
        qs = '日本'
        res, results = query_public_search(self, qs, self.user1)
        assert_equal(res.status_code, 400)
        DEBUG('results', results)
        assert_equal(results, None)

        res, results = query_private_search(self, qs, self.user1)
        assert_equal(res.status_code, 400)
        DEBUG('results', results)
        assert_equal(results, None)

    @enable_private_search
    def test_private_search_user1(self):
        """
        user1 がアクセス可能なプロジェクトに関するデータを検索できるこ
        とを確認する。
        プライベートなプロジェクトに所属するタグとファイル名が有る場合。
        """
        qs = '日本語'
        res, results = query_private_search(self, qs, self.user1)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user1_1.title)
        tags = get_tags(results, self.project_private_user1_1.title)
        filenames = get_filenames(results)
        category_count_map = get_category_count_map(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)
        DEBUG('category count', category_count_map)

        assert_equal(len(results), 9)
        assert_equal(category_count_map['user'], 2)
        assert_equal(category_count_map['project'], 4)
        assert_equal(category_count_map['file'], 3)
        assert_equal(len(user_fullnames), 2)
        assert_equal(len(node_titles), 4)  # private=2, public=2
        assert_equal(len(contributors), 1)
        assert_equal(len(tags), 3)
        assert_equal(len(filenames), 3)
        assert_not_in(
            s2u(self.project_private_user2_1.title),
            s2u(node_titles)
        )
        assert_not_in(
            s2u(self.project_private_user2_2.title),
            s2u(node_titles)
        )
        assert_not_in(
            s2u(self.user2.fullname),
            s2u(contributors)
        )

    @enable_private_search
    def test_private_search_user2(self):
        """
        user2 がアクセス可能なプロジェクトに関するデータを検索できるこ
        とを確認する。
        プライベートなプロジェクトに所属するタグとファイル名が無い場合。
        """
        qs = '日本語'
        res, results = query_private_search(self, qs, self.user2)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user2_1.title)
        tags = get_tags(results, self.project_private_user2_1.title)
        filenames = get_filenames(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)

        assert_equal(len(results), 6)  # user=2, project=4, file=0
        assert_equal(len(user_fullnames), 2)
        assert_equal(len(node_titles), 4)  # private=2, public=2
        assert_equal(len(contributors), 1)
        assert_equal(len(tags), 0)
        assert_equal(len(filenames), 0)
        assert_not_in(
            s2u(self.project_private_user1_1.title),
            s2u(node_titles)
        )
        assert_not_in(
            s2u(self.user1.fullname),
            s2u(contributors)
        )

    @enable_private_search
    def test_no_match(self):
        """
        「本日」は「日本」にマッチしないことを確認する。
        """
        qs = '本日'
        res, results = query_private_search(self, qs, self.user2)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user2_1.title)
        tags = get_tags(results, self.project_private_user2_1.title)
        filenames = get_filenames(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)

        assert_equal(len(results), 0)
        assert_equal(len(user_fullnames), 0)
        assert_equal(len(node_titles), 0)
        assert_equal(len(contributors), 0)
        assert_equal(len(tags), 0)
        assert_equal(len(filenames), 0)

    @enable_private_search
    def test_tags(self):
        """
        タグを検索できることを確認する。
        tagsフィールド全体に完全一致する必要がある。
        """
        qs = 'tags:("日本語タグ")'
        res, results = query_private_search(self, qs, self.user1)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user1_1.title)
        tags = get_tags(results, self.project_private_user1_1.title)
        filenames = get_filenames(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)

        assert_equal(len(results), 1)
        assert_equal(len(user_fullnames), 0)
        assert_equal(len(node_titles), 1)
        assert_equal(len(contributors), 1)
        assert_equal(len(tags), 3)
        assert_equal(len(filenames), 0)

    @enable_private_search
    def test_tags_no_match(self):
        """
        タグを部分一致で検索できないことを確認する。
        """
        qs = 'tags:日本語'
        res, results = query_private_search(self, qs, self.user1)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user1_1.title)
        tags = get_tags(results, self.project_private_user1_1.title)
        filenames = get_filenames(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)

        assert_equal(len(results), 0)
        assert_equal(len(user_fullnames), 0)
        assert_equal(len(node_titles), 0)
        assert_equal(len(contributors), 0)
        assert_equal(len(tags), 0)
        assert_equal(len(filenames), 0)


    @enable_private_search
    def test_file(self):
        """
        ファイル名を検索できることを確認する。
        AND 式も使用して、ファイル名に含まれる文字をさらに限定している。
        """
        qs = 'category:file && 日本語ファイル'
        res, results = query_private_search(self, qs, self.user1)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user1_1.title)
        tags = get_tags(results, self.project_private_user1_1.title)
        filenames = get_filenames(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)

        assert_equal(len(results), 1)  # file=1
        assert_equal(len(user_fullnames), 0)
        assert_equal(len(node_titles), 0)
        assert_equal(len(contributors), 0)
        assert_equal(len(tags), 0)
        assert_equal(len(filenames), 1)

    @enable_private_search
    def _common_normalize(self, qs, category=None, user=None, version=1):
        return query_for_normalize_tests(self, qs, category=category,
                                         user=user, version=version)

    def test_normalize_user1(self):
        """
        Unicode正規化のテスト。通常検索でUserを検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'category:user AND \u304c'  # が
        res, results = self._common_normalize(qs)
        user_fullnames = get_user_fullnames(results)
        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        assert_equal(len(results), 1)
        assert_equal(len(user_fullnames), 1)

    def test_normalize_user2(self):
        """
        Unicode正規化のテスト。通常検索でUserを検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'category:user AND \u304d\u3099'  # き+濁点
        res, results = self._common_normalize(qs)
        user_fullnames = get_user_fullnames(results)
        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        assert_equal(len(results), 1)
        assert_equal(len(user_fullnames), 1)

    @enable_private_search
    def _set_job_school(self, user, nmlz):
        def job(inst, depart, title, ongoing):
            return {
                'institution': nmlz(inst),
                'department': nmlz(depart),
                'title': nmlz(title),
                'ongoing': ongoing,
            }

        def school(inst, depart, degree, ongoing):
            return {
                'institution': nmlz(inst),
                'department':nmlz(depart),
                'degree': nmlz(degree),
                'ongoing': ongoing,
            }

        with run_celery_tasks():
            user.jobs = []
            user.jobs.append(
                job(u'かきくけこ', u'さしすせそ', u'たちつてと', False))
            user.jobs.append(
                job(u'がぎぐげご', u'ざじずぜぞ', u'だぢづでど', True))
            user.jobs.append(
                job(u'NG', u'NG', u'NG', True))
            user.schools = []
            user.schools.append(
                school(u'カキクケコ', u'サシスセソ', u'タチツテト', False))
            user.schools.append(
                school(u'ガギグゲゴ', u'ザジズゼゾ', u'ダヂヅデド', True))
            user.schools.append(
                school(u'NG', u'NG', u'NG', True))
            user.save()

    def test_normalize_user_ongoing_job_school(self):
        """
        Unicode正規化のテスト。通常検索でUserのprofileを検索する場合。
        データベースに登録されている濁点付き文字が
        結合可能濁点と母体の文字の組み合わせ(結合文字)の場合と、
        または合成済み文字の場合とで、検索する場合の濁点文字列の
        正規化手段を反対にして検索できることを確認する。
        同時に、ongoingがTrueかつ一件目の所属情報を返すことも確認する。
        """
        hga = (u'がぎぐげご', 'job')
        hza = (u'ざじずぜぞ', 'job_department')
        hda = (u'だぢづでど', 'job_title')
        kga = (u'ガギグゲゴ', 'school')
        kza = (u'ザジズゼゾ', 'school_department')
        kda = (u'ダヂヅデド', 'school_degree')
        all_ = (hga, hza, hda, kga, kza, kda)

        self._set_job_school(self.user3, nfd)  # 結合文字をDBに格納

        def test1():
            for p in all_:
                qs = nfc(p[0])  # 合成済み文字で検索
                res, results = self._common_normalize(qs, 'user')
                user_fullnames = get_user_fullnames(results)
                DEBUG('results', results)
                assert_equal(len(results), 1)
                r = results[0]
                assert_equal(r['ongoing_' + p[1]], nfd(p[0]))  # DB側の形式

        run_after_rebuild_search(self, test1)

        self._set_job_school(self.user3, nfc)  # 合成済み文字をDBに格納

        def test2():
            for p in all_:
                qs = nfd(p[0])  # 結合文字で検索
                res, results = self._common_normalize(qs, 'user')
                user_fullnames = get_user_fullnames(results)
                DEBUG('results', results)
                assert_equal(len(results), 1)
                r = results[0]
                assert_equal(r['ongoing_' + p[1]], nfc(p[0]))  # DB側の形式

        run_after_rebuild_search(self, test2)

    def test_normalize_prj_title1(self):
        """
        Unicode正規化のテスト。通常検索でtitleを検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'category:project AND \u305e'  # ぞ
        res, results = self._common_normalize(qs, user=self.user4)
        node_titles = get_node_titles(results)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)

    def test_normalize_prj_title2(self):
        """
        Unicode正規化のテスト。通常検索でtitleを検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'category:project AND \u3053\u3099'  # こ+濁点
        res, results = self._common_normalize(qs, user=self.user3)
        node_titles = get_node_titles(results)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)

    def test_normalize_prj_description1(self):
        """
        Unicode正規化のテスト。通常検索でdescriptionを検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'category:project AND \u3050'  # ぐ
        res, results = self._common_normalize(qs)
        node_titles = get_node_titles(results)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)

    def test_normalize_prj_description2(self):
        """
        Unicode正規化のテスト。通常検索でdescriptionを検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'category:project AND \u3051\u3099'  # け+濁点
        res, results = self._common_normalize(qs)
        node_titles = get_node_titles(results)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)

    def test_normalize_prj_creator1(self):
        """
        Unicode正規化のテスト。通常検索でプロジェクトcreatorを検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'category:project AND \u304c'  # が
        res, results = self._common_normalize(qs, user=self.user3)
        node_titles = get_node_titles(results)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        r = results[0]
        c = u'\u304b\u3099' # か+濁点
        assert_equal(r['creator_id'], self.user3._id)
        assert_equal(r['creator_name'], c)

    def test_normalize_prj_creator2(self):
        """
        Unicode正規化のテスト。通常検索でプロジェクトcreatorを検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        c1 = u'\u304d\u3099'  # き+濁点
        qs = u'category:project AND ' + c1
        res, results = self._common_normalize(qs, user=self.user4)
        node_titles = get_node_titles(results)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        r = results[0]
        c2 = u'\u304e' # ぎ
        assert_equal(r['creator_id'], self.user4._id)
        assert_equal(r['creator_name'], c2)

    def test_normalize_prj_modifier1(self):
        """
        Unicode正規化のテスト。通常検索でプロジェクトmodifierを検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        c1 = u'\u3070'  # ば
        qs = u'category:project AND ' + c1
        res, results = self._common_normalize(qs, user=self.user3)
        node_titles = get_node_titles(results)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        r = results[0]
        c2 = u'\u306f\u3099' # は+濁点
        assert_equal(r['modifier_id'], self.user5._id)
        assert_equal(r['modifier_name'], c2)

    def test_normalize_prj_modifier2(self):
        """
        Unicode正規化のテスト。通常検索でプロジェクトmodifierを検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        c1 = u'\u3072\u3099'  # ひ+濁点
        qs = u'category:project AND ' + c1
        res, results = self._common_normalize(qs, user=self.user4)
        node_titles = get_node_titles(results)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        r = results[0]
        c2 = u'\u3073' # び
        assert_equal(r['modifier_id'], self.user6._id)
        assert_equal(r['modifier_name'], c2)

    def test_normalize_prj_wikiname1(self):
        """
        Unicode正規化のテスト。通常検索でwikiページ名を検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'category:project AND \u3056'  # ざ
        res, results = self._common_normalize(qs, 'project', version=1)
        node_titles = get_node_titles(results)
        tags = get_tags(results, self.project_private_user1_1.title)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        DEBUG('tags', tags)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        assert_equal(len(tags), 3)

    def test_normalize_prj_wikiname2(self):
        """
        Unicode正規化のテスト。通常検索でwikiページ名を検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'category:project AND \u3057\u3099'  # し+濁点
        res, results = self._common_normalize(qs, 'project', version=1)
        node_titles = get_node_titles(results)
        tags = get_tags(results, self.project_private_user1_1.title)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        DEBUG('tags', tags)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        assert_equal(len(tags), 3)

    def test_normalize_prj_wikicontent1(self):
        """
        Unicode正規化のテスト。通常検索でwikiページ本文を検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'category:project AND \u305a'  # ず
        res, results = self._common_normalize(qs, 'project', version=1)
        node_titles = get_node_titles(results)
        tags = get_tags(results, self.project_private_user1_1.title)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        DEBUG('tags', tags)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        assert_equal(len(tags), 3)

    def test_normalize_prj_wikicontent2(self):
        """
        Unicode正規化のテスト。通常検索でwikiページ本文を検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'category:project AND \u305b\u3099'  # せ+濁点
        res, results = self._common_normalize(qs, 'project', version=1)
        node_titles = get_node_titles(results)
        tags = get_tags(results, self.project_private_user1_1.title)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        DEBUG('tags', tags)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        assert_equal(len(tags), 3)

    def test_normalize_filename1(self):
        """
        Unicode正規化のテスト。通常検索でファイル名を検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'\u3060'  # だ
        res, results = self._common_normalize(qs)
        filenames = get_filenames(results)
        DEBUG('results', results)
        DEBUG('filenames', filenames)
        assert_equal(len(results), 1)
        assert_equal(len(filenames), 1)

    def test_normalize_filename2(self):
        """
        Unicode正規化のテスト。通常検索でファイル名を検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'\u3061\u3099'  # ち+濁点
        res, results = self._common_normalize(qs)
        filenames = get_filenames(results)
        DEBUG('results', results)
        DEBUG('filenames', filenames)
        assert_equal(len(results), 1)
        assert_equal(len(filenames), 1)

    def test_normalize_tags1(self):
        """
        Unicode正規化のテスト。通常検索でtagsを検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'tags:\u3065'  # づ
        res, results = self._common_normalize(qs)
        node_titles = get_node_titles(results)
        tags = get_tags(results, self.project_private_user1_1.title)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        DEBUG('tags', tags)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        assert_equal(len(tags), 3)

    def test_normalize_tags2(self):
        """
        Unicode正規化のテスト。通常検索でtagsを検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'tags:\u3066\u3099'  # て+濁点
        res, results = self._common_normalize(qs)
        node_titles = get_node_titles(results)
        tags = get_tags(results, self.project_private_user1_1.title)
        DEBUG('results', results)
        DEBUG('node_titles', node_titles)
        DEBUG('tags', tags)
        assert_equal(len(results), 1)
        assert_equal(len(node_titles), 1)
        assert_equal(len(tags), 3)

    def test_normalize_filetags1(self):
        """
        Unicode正規化のテスト。通常検索でファイルのtagsを検索する場合。
        データベースに登録されている半角数字を全角数字で検索できる
        ことを確認する。
        """
        qs = u'tags:\uff11\uff12\uff13\uff14\uff15'  # １２３４５
        res, results = self._common_normalize(qs)
        filenames = get_filenames(results)
        tags = get_filetags(results, self.f1.name)
        DEBUG('results', results)
        DEBUG('filenames', filenames)
        DEBUG('tags', tags)
        assert_equal(len(results), 1)
        assert_equal(len(filenames), 1)
        assert_equal(len(tags), 2)

    def test_normalize_filetags2(self):
        """
        Unicode正規化のテスト。通常検索でファイルのtagsを検索する場合。
        データベースに登録されている全角数字を半角数字で検索できる
        ことを確認する。
        """
        qs = u'tags:67890'
        res, results = self._common_normalize(qs)
        filenames = get_filenames(results)
        tags = get_filetags(results, self.f1.name)
        DEBUG('results', results)
        DEBUG('filenames', filenames)
        DEBUG('tags', tags)
        assert_equal(len(results), 1)
        assert_equal(len(filenames), 1)
        assert_equal(len(tags), 2)

    @enable_private_search
    def _update_file(self, project, user, count):
        with run_celery_tasks():
            osfstorage = project.get_addon('osfstorage')
            root_node = osfstorage.get_root()
            name = 'test_file'
            test_file = update_dummy_file(user, root_node, name, count)

        assert_equal(test_file.versions.count(), count)
        # first() of file.versions is latest
        assert_equal(test_file.versions.all().first().creator, user)

    def test_normalize_file_creator_modifier1(self):
        """
        Unicode正規化のテスト。通常検索でファイルのcreatorとmodifier
        をそれぞれ検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        def test1():
            c1 = u'\u304c'  # が (user3)
            qs = u'category:file AND creator_name:' + c1
            res, results = self._common_normalize(qs, user=self.user3)
            filenames = get_filenames(results)
            tags = get_filetags(results, self.f1.name)
            DEBUG('results', results)
            DEBUG('filenames', filenames)
            DEBUG('tags', tags)
            assert_equal(len(results), 1)
            assert_equal(len(filenames), 1)
            assert_equal(len(tags), 0)
            r = results[0]
            c2 = u'\u304b\u3099' # か+濁点
            assert_equal(r['creator_id'], self.user3._id)
            assert_equal(r['creator_name'], c2)

            c1 = u'\u3070'  # ば (user5)
            qs = u'category:file AND modifier_name:' + c1
            res, results = self._common_normalize(qs, user=self.user3)
            filenames = get_filenames(results)
            tags = get_filetags(results, self.f1.name)
            DEBUG('results', results)
            DEBUG('filenames', filenames)
            DEBUG('tags', tags)
            assert_equal(len(results), 1)
            assert_equal(len(filenames), 1)
            assert_equal(len(tags), 0)
            r = results[0]
            c2 = u'\u306f\u3099' # は+濁点
            assert_equal(r['modifier_id'], self.user5._id)
            assert_equal(r['modifier_name'], c2)

        # creator
        self._update_file(self.project_private_user3, self.user3, 1)
        # modifier
        self._update_file(self.project_private_user3, self.user5, 2)
        run_after_rebuild_search(self, test1)

    def test_normalize_file_creator_modifier2(self):
        """
        Unicode正規化のテスト。通常検索でファイルのcreatorとmodifier
        をそれぞれ検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        def test1():
            c1 = u'\u304d\u3099'  # き+濁点 (user4)
            qs = u'category:file AND creator_name:' + c1
            res, results = self._common_normalize(qs, user=self.user4)
            filenames = get_filenames(results)
            tags = get_filetags(results, self.f1.name)
            DEBUG('results', results)
            DEBUG('filenames', filenames)
            DEBUG('tags', tags)
            assert_equal(len(results), 1)
            assert_equal(len(filenames), 1)
            assert_equal(len(tags), 0)
            r = results[0]
            c2 = u'\u304e' # ぎ
            assert_equal(r['creator_id'], self.user4._id)
            assert_equal(r['creator_name'], c2)

            c1 = u'\u3072\u3099'  # ひ+濁点 (user6)
            qs = u'category:file AND modifier_name:' + c1
            res, results = self._common_normalize(qs, user=self.user4)
            filenames = get_filenames(results)
            tags = get_filetags(results, self.f1.name)
            DEBUG('results', results)
            DEBUG('filenames', filenames)
            DEBUG('tags', tags)
            assert_equal(len(results), 1)
            assert_equal(len(filenames), 1)
            assert_equal(len(tags), 0)
            r = results[0]
            c2 = u'\u3073'  # び
            assert_equal(r['modifier_id'], self.user6._id)
            assert_equal(r['modifier_name'], c2)

        # creator
        self._update_file(self.project_private_user4, self.user4, 1)
        # modifier
        self._update_file(self.project_private_user4, self.user6, 2)
        run_after_rebuild_search(self, test1)

    @enable_private_search
    def _common_normalize_search_contributor(self, qs):
        # app.get() requires str
        qs = u2s(qs)
        res, results = query_search_contributor(self, qs, self.user1)

        # get_user_fullnames() cannot be used for query_search_contributor().
        user_fullnames = [r['fullname'] for r in results]
        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        assert_equal(len(results), 1)
        assert_equal(len(user_fullnames), 1)

    def test_normalize_search_contributor1(self):
        """
        Unicode正規化のテスト。Add Contributorsにおける検索の場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'\u304c'  # が
        self._common_normalize_search_contributor(qs)

    def test_normalize_search_contributor2(self):
        """
        Unicode正規化のテスト。Add Contributorsにおける検索の場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'\u304d\u3099'  # き+濁点
        self._common_normalize_search_contributor(qs)

    @enable_private_search
    def test_search_invalid_version(self):
        """
        検索APIに含まれるバージョンが想定しない形式の場合に
        BAD_REQUEST になることを確認する。
        """

        def build_invalid_query1(query_string, version, vendor):
            return {
                'api_version': {
                    'version': version,
                    'vendor': vendor
                },
                'elasticsearch_dsl': build_query(query_string)
            }

        def build_invalid_query2(query_string):
            return build_query(query_string)

        def bad_request(query):
            res = self.app.post_json(
                api_url_for('search_search'),
                query,
                auth=self.user1.auth,
                expect_errors=True
            )
            assert_equal(res.status_code, 400)

        qs = 'てすと'
        bad_request(build_invalid_query1(qs, 1000, 'grdm'))
        bad_request(build_invalid_query1(qs, 1, '__invalid_vendor__'))
        bad_request(build_invalid_query2(qs))

    @enable_private_search
    def test_unauthorized(self):
        """
        ログインしていない場合は、検索APIと検索ページにアクセス
        できないことを確認する。
        検索ページの場合は、リダイレクトすることを確認する。
        """
        qs = 'てすと'
        res = self.app.post_json(
            api_url_for('search_search'),
            build_private_search_query(qs),
            auth=None,
            expect_errors=True
        )
        assert_equal(res.status_code, 401)  # Unauthorized

        res = self.app.get(
            api_url_for('search_search'),
            auth=None,
            expect_errors=True
        )
        assert_equal(res.status_code, 401)  # Unauthorized

        # view
        url = web_url_for('search_view', _absolute=True)
        res = self.app.get(url, auth=None)
        assert_equal(res.status_code, 302)

    _use_migrate = False

    @enable_private_search
    def test_after_rebuild_search(self):
        """
        invoke rebuild_search 相当の migrate() を実行後、
        TestPrivateSearch の各テストが成功することを確認する。
        """
        my_method_name = sys._getframe().f_code.co_name
        run_test_all_after_rebuild_search(self, my_method_name)


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchExt(OsfTestCase):

    @enable_private_search
    def setUp(self):
        setup(TestSearchExt, self)

    @enable_private_search
    def tearDown(self):
        tear_down(TestSearchExt, self)

    @enable_private_search
    def test_private_search_user1_ext(self):
        """
        test_private_search_user1と同様の検索をversion=2で実行し、
        user1だけがアクセス可能なwikiとcommentを検索できることを確認する。
        """
        qs = '日本語'
        res, results = query_private_search(self, qs, self.user1, version=2)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user1_1.title)
        tags = get_tags(results, self.project_private_user1_1.title)
        filenames = get_filenames(results)
        category_count_map = get_category_count_map(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)
        DEBUG('category count', category_count_map)

        assert_equal(len(results), 11)
        assert_equal(category_count_map['user'], 2)
        assert_equal(category_count_map['project'], 4)
        assert_equal(category_count_map['file'], 3)
        assert_equal(category_count_map['wiki'], 2)
        assert_equal(len(user_fullnames), 2)
        assert_equal(len(node_titles), 4)  # private=2, public=2
        assert_equal(len(contributors), 1)
        assert_equal(len(tags), 3)
        assert_equal(len(filenames), 3)
        assert_not_in(
            s2u(self.project_private_user2_1.title),
            s2u(node_titles)
        )
        assert_not_in(
            s2u(self.project_private_user2_2.title),
            s2u(node_titles)
        )
        assert_not_in(
            s2u(self.user2.fullname),
            s2u(contributors)
        )

    @enable_private_search
    def _common_normalize(self, qs, category=None, user=None, version=1):
        return query_for_normalize_tests(self, qs, category=category,
                                         user=user, version=version)

    def test_normalize_wiki_name1(self):
        """
        Unicode正規化のテスト。通常検索でwikiページ名を検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'\u3056'  # ざ
        res, results = self._common_normalize(qs, 'wiki', version=2)
        DEBUG('results', results)
        assert_equal(len(results), 1)
        r = results[0]
        c2 = u'\u3055\u3099' # さ+濁点
        assert_equal(r['name'], c2)

    def test_normalize_wiki_name2(self):
        """
        Unicode正規化のテスト。通常検索でwikiページ名を検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        qs = u'category:wiki AND \u3057\u3099'  # し+濁点
        res, results = self._common_normalize(qs, version=2)
        DEBUG('results', results)
        assert_equal(len(results), 1)
        r = results[0]
        c2 = u'\u3058' # じ
        assert_equal(r['name'], c2)

    def test_normalize_wiki_content1(self):
        """
        Unicode正規化のテスト。通常検索でwikiページ本文を検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        qs = u'\u305a'  # ず
        res, results = self._common_normalize(qs, 'wiki', version=2)
        DEBUG('results', results)
        assert_equal(len(results), 1)
        r = results[0]
        # text is not return to original strings.
        c2 = u'\u3059\u3099' # す+濁点
        assert_equal(r['text'], c2)

    def test_normalize_wiki_content2(self):
        """
        Unicode正規化のテスト。通常検索でwikiページ本文を検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        c1 = u'\u305b\u3099'  # せ+濁点
        qs = u'category:wiki AND ' + c1
        res, results = self._common_normalize(qs, version=2)
        DEBUG('results', results)
        assert_equal(len(results), 1)
        r = results[0]
        assert_equal(r['text'], c1)
        # c2 = u'\u305c' # ぜ
        # assert_not_equal(r['text'], c2)

    @enable_private_search
    def _update_wiki(self, project, user, count):
        with run_celery_tasks():
            name = 'test_wiki'
            content = 'content wiki' + str(count)
            wiki = WikiPage.objects.get_for_node(project, name)
            if wiki:
                wiki.update(user, content)
            else:
                wiki = WikiPage.objects.create_for_node(
                    project, name, content, Auth(user))

        assert_equal(wiki.versions.count(), count)
        # latest
        assert_equal(wiki.get_versions().first().user, user)

    def test_normalize_wiki_creator_modifier1(self):
        """
        Unicode正規化のテスト。通常検索でWikiのcreatorとmodifier
        をそれぞれ検索する場合。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        """
        # creator
        self._update_wiki(self.project_private_user3, self.user3, 1)
        # modifier
        self._update_wiki(self.project_private_user3, self.user5, 2)

        def test1():
            c1 = u'\u304c'  # が (user3)
            qs = u'category:wiki AND creator_name:' + c1
            res, results = self._common_normalize(qs, user=self.user3, version=2)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            c2 = u'\u304b\u3099' # か+濁点
            assert_equal(r['creator_id'], self.user3._id)
            assert_equal(r['creator_name'], c2)

            c1 = u'\u3070'  # ば (user5)
            qs = u'category:wiki AND modifier_name:' + c1
            res, results = self._common_normalize(qs, user=self.user3, version=2)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            c2 = u'\u306f\u3099' # は+濁点
            assert_equal(r['modifier_id'], self.user5._id)
            assert_equal(r['modifier_name'], c2)

        run_after_rebuild_search(self, test1)

    def test_normalize_wiki_creator_modifier2(self):
        """
        Unicode正規化のテスト。通常検索でWikiのcreatorとmodifier
        をそれぞれ検索する場合。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        """
        # creator
        self._update_wiki(self.project_private_user4, self.user4, 1)
        # modifier
        self._update_wiki(self.project_private_user4, self.user6, 2)

        def test1():
            c1 = u'\u304d\u3099'  # き+濁点 (user4)
            qs = u'category:wiki AND creator_name:' + c1
            res, results = self._common_normalize(qs, user=self.user4, version=2)
            filenames = get_filenames(results)
            tags = get_filetags(results, self.f1.name)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            c2 = u'\u304e' # ぎ
            assert_equal(r['creator_id'], self.user4._id)
            assert_equal(r['creator_name'], c2)

            c1 = u'\u3072\u3099'  # ひ+濁点 (user6)
            qs = u'category:wiki AND modifier_name:' + c1
            res, results = self._common_normalize(qs, user=self.user4, version=2)
            filenames = get_filenames(results)
            tags = get_filetags(results, self.f1.name)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            c2 = u'\u3073'  # び
            assert_equal(r['modifier_id'], self.user6._id)
            assert_equal(r['modifier_name'], c2)

        run_after_rebuild_search(self, test1)

    _use_migrate = False

    @enable_private_search
    def test_after_rebuild_search_for_ext(self):
        """
        invoke rebuild_search 相当の migrate() を実行後、
        TestSearchExt の各テストが成功することを確認する。
        """
        my_method_name = sys._getframe().f_code.co_name
        run_test_all_after_rebuild_search(self, my_method_name)


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchHighlight(OsfTestCase):

    @enable_private_search
    def setUp(self):
        setup(TestSearchHighlight, self, create_obj=False)

    @enable_private_search
    def tearDown(self):
        tear_down(TestSearchHighlight, self)

    tag1 = u'<b>'
    tag2 = u'</b>'
    taglen = len(tag1 + tag2)

    def _tagged(self, text):
        return self.tag1 + nfd(text) + self.tag2

    def _gen_text(self, base, size=400):
        len_kanji = int(size / 2)
        tmp = []
        for i in range(len_kanji):
            tmp.append(u'漢')
        tmp.append(base)
        for i in range(len_kanji):
            tmp.append(u'漢')
        return ''.join(tmp)

    @enable_private_search
    def test_highlight_prj_comment(self):
        """
        プロジェクトに付加したコメントを検索できることを確認する。
        マッチしたコメントのうち、最後のコメントであることを確認する。
        コメントはスニペットになっていることを確認する。
        コメントしたユーザーの情報があることを確認する。
        返信コメントの場合は返信相手の情報があることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            u2 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(creator=u1, is_public=False)
            c_old = factories.CommentFactory(
                node=p1, user=u1, page=Comment.OVERVIEW,
                content=u'ぎぐげ')  # old and short comment
            c1 = factories.CommentFactory(
                node=p1, user=u1, page=Comment.OVERVIEW,
                content=self._gen_text(u'がぎぐげご'))
            c2_reply = factories.CommentFactory(
                node=p1, user=u2, page=Comment.OVERVIEW,
                target=Guid.load(c1._id),
                content=self._gen_text(u'ざじずぜぞ'))

        def _search(qs):
            return query_private_search(
                self, qs, u1, category='project', version=2)

        def test1():
            qs = u'ぎぐげ'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            comment = r.get('comment')
            assert_equal(comment['user_id'], u1._id)
            assert_equal(comment['user_name'], u1.fullname)
            assert_equal(comment['replyto_user_id'], None)
            assert_equal(comment['replyto_user_name'], None)
            assert_in(self._tagged(qs), comment['text'])
            size = len(comment['text'])
            assert_greater_equal(size, HIGHLIGHT_SIZE_TEXT)
            assert_less_equal(size, HIGHLIGHT_SIZE_TEXT + self.taglen)

            qs = u'じずぜ'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            comment = r.get('comment')
            assert_equal(comment['user_id'], u2._id)
            assert_equal(comment['user_name'], u2.fullname)
            assert_equal(comment['replyto_user_id'], u1._id)
            assert_equal(comment['replyto_user_name'], u1.fullname)
            assert_in(self._tagged(qs), comment['text'])
            size = len(comment['text'])
            assert_greater_equal(size, HIGHLIGHT_SIZE_TEXT)
            assert_less_equal(size, HIGHLIGHT_SIZE_TEXT + self.taglen)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_highlight_file_comment(self):
        """
        ファイルに付加したコメントを検索できることを確認する。
        マッチしたコメントのうち、最後のコメントであることを確認する。
        コメントはスニペットになっていることを確認する。
        コメントしたユーザーの情報があることを確認する。
        返信コメントの場合は返信相手の情報があることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            u2 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(creator=u1, is_public=False)
            rootdir = p1.get_addon('osfstorage').get_root()
            f1 = api_utils.create_test_file(p1, u1, create_guid=True)
            c_old = factories.CommentFactory(
                node=p1, user=u1, page=Comment.FILES,
                target=f1.get_guid(create=False),
                content=u'ぎぐげ')  # old and short comment
            c1 = factories.CommentFactory(
                node=p1, user=u1, page=Comment.FILES,
                target=f1.get_guid(create=False),
                content=self._gen_text(u'がぎぐげご'))
            c2_reply = factories.CommentFactory(
                node=p1, user=u2, page=Comment.FILES,
                target=Guid.load(c1._id),
                content=self._gen_text(u'ざじずぜぞ'))

        def _search(qs):
            return query_private_search(
                self, qs, u1, category='file', version=2)

        def test1():
            qs = u'ぎぐげ'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            comment = r.get('comment')
            assert_equal(comment['user_id'], u1._id)
            assert_equal(comment['user_name'], u1.fullname)
            assert_equal(comment['replyto_user_id'], None)
            assert_equal(comment['replyto_user_name'], None)
            assert_in(self._tagged(qs), comment['text'])
            size = len(comment['text'])
            assert_greater_equal(size, HIGHLIGHT_SIZE_TEXT)
            assert_less_equal(size, HIGHLIGHT_SIZE_TEXT + self.taglen)

            qs = u'じずぜ'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            comment = r.get('comment')
            assert_equal(comment['user_id'], u2._id)
            assert_equal(comment['user_name'], u2.fullname)
            assert_equal(comment['replyto_user_id'], u1._id)
            assert_equal(comment['replyto_user_name'], u1.fullname)
            assert_in(self._tagged(qs), comment['text'])
            size = len(comment['text'])
            assert_greater_equal(size, HIGHLIGHT_SIZE_TEXT)
            assert_less_equal(size, HIGHLIGHT_SIZE_TEXT + self.taglen)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_highlight_wiki_comment(self):
        """
        Wikiに付加したコメントを検索できることを確認する。
        マッチしたコメントのうち、最後のコメントであることを確認する。
        コメントはスニペットになっていることを確認する。
        コメントしたユーザーの情報があることを確認する。
        返信コメントの場合は返信相手の情報があることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            u2 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(creator=u1, is_public=False)
            w1 = WikiPage.objects.create_for_node(
                p1, 'test_wiki', 'test_wiki', Auth(u1))
            c_old = factories.CommentFactory(
                node=p1, user=u1, page=Comment.WIKI,
                target=Guid.load(w1._id),
                content=u'ぎぐげ')  # old and short comment
            c1 = factories.CommentFactory(
                node=p1, user=u1, page=Comment.WIKI,
                target=Guid.load(w1._id),
                content=self._gen_text(u'がぎぐげご'))
            c2_reply = factories.CommentFactory(
                node=p1, user=u2, page=Comment.WIKI,
                target=Guid.load(c1._id),
                content=self._gen_text(u'ざじずぜぞ'))

        def _search(qs):
            return query_private_search(
                self, qs, u1, category='wiki', version=2)

        def test1():
            qs = u'ぎぐげ'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            comment = r.get('comment')
            assert_equal(comment['user_id'], u1._id)
            assert_equal(comment['user_name'], u1.fullname)
            assert_equal(comment['replyto_user_id'], None)
            assert_equal(comment['replyto_user_name'], None)
            assert_in(self._tagged(qs), comment['text'])
            size = len(comment['text'])
            assert_greater_equal(size, HIGHLIGHT_SIZE_TEXT)
            assert_less_equal(size, HIGHLIGHT_SIZE_TEXT + self.taglen)

            qs = u'じずぜ'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            comment = r.get('comment')
            assert_equal(comment['user_id'], u2._id)
            assert_equal(comment['user_name'], u2.fullname)
            assert_equal(comment['replyto_user_id'], u1._id)
            assert_equal(comment['replyto_user_name'], u1.fullname)
            assert_in(self._tagged(qs), comment['text'])
            size = len(comment['text'])
            assert_greater_equal(size, HIGHLIGHT_SIZE_TEXT)
            assert_less_equal(size, HIGHLIGHT_SIZE_TEXT + self.taglen)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_highlight_project_title(self):
        """
        プロジェクト名のスニペットが返ることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(
                title=self._gen_text(u'だぢづでど', 100),
                creator=u1, is_public=False)

        def _search(qs):
            return query_private_search(
                self, qs, u1, category='project', version=2)

        def test1():
            qs = u'ぢづで'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            assert_equal(r['id'], p1._id)
            title = r['highlight']['title'][0]
            assert_in(self._tagged(qs), title)
            size = len(title)
            assert_greater_equal(size, HIGHLIGHT_SIZE_TITLE)
            assert_less_equal(size, HIGHLIGHT_SIZE_TITLE + self.taglen)

    @enable_private_search
    def test_highlight_file_name(self):
        """
        ファイル名のスニペットが返ることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(creator=u1, is_public=False)
            rootdir = p1.get_addon('osfstorage').get_root()
            f1 = api_utils.create_test_file(
                p1, u1,
                filename=self._gen_text(u'だぢづでど', 100),
                create_guid=True)

        def _search(qs):
            return query_private_search(
                self, qs, u1, category='file', version=2)

        def test1():
            qs = u'ぢづで'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            assert_equal(r['id'], f1._id)
            title = r['highlight']['name'][0]
            assert_in(self._tagged(qs), title)
            size = len(title)
            assert_greater_equal(size, HIGHLIGHT_SIZE_TITLE)
            assert_less_equal(size, HIGHLIGHT_SIZE_TITLE + self.taglen)

    @enable_private_search
    def test_highlight_wiki_title_text(self):
        """
        Wikiのページ名と内容のスニペットが返ることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(creator=u1, is_public=False)
            w1 = WikiPage.objects.create_for_node(
                p1,
                self._gen_text(u'だぢづでど', 100),
                self._gen_text(u'ばびぶべぼ'),
                Auth(u1))

        def _search(qs):
            return query_private_search(
                self, qs, u1, category='wiki', version=2)

        def test1():
            qs = u'ぢづで'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            assert_equal(r['id'], w1._id)
            title = r['highlight']['name'][0]
            assert_in(self._tagged(qs), title)
            size = len(title)
            assert_greater_equal(size, HIGHLIGHT_SIZE_TITLE)
            assert_less_equal(size, HIGHLIGHT_SIZE_TITLE + self.taglen)

            qs = u'びぶべ'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            assert_equal(r['id'], w1._id)
            text = r['highlight']['text'][0]
            assert_in(self._tagged(qs), text)
            size = len(text)
            assert_greater_equal(size, HIGHLIGHT_SIZE_TEXT)
            assert_less_equal(size, HIGHLIGHT_SIZE_TEXT + self.taglen)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_highlight_user_name(self):
        """
        ユーザーのfullnameのスニペットが返ることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory(
                fullname=self._gen_text(u'だぢづでど', 100))

        def _search(qs):
            return query_private_search(
                self, qs, u1, category='user', version=2)

        def test1():
            qs = u'ぢづで'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            assert_equal(r['id'], u1._id)
            title = r['highlight']['user'][0]
            assert_in(self._tagged(qs), title)
            size = len(title)
            assert_greater_equal(size, HIGHLIGHT_SIZE_TITLE)
            assert_less_equal(size, HIGHLIGHT_SIZE_TITLE + self.taglen)

    @enable_private_search
    def test_highlight_institution_name(self):
        """
        機関名のスニペットが返ることを確認する。
        """
        with run_celery_tasks():
            i1 = factories.InstitutionFactory(
                name=self._gen_text(u'だぢづでど', 100))

        def _search(qs):
            return query_private_search(
                self, qs, u1, category='institution', version=2)

        def test1():
            qs = u'ぢづで'
            res, results = _search(qs)
            DEBUG('results', results)
            assert_equal(len(results), 1)
            r = results[0]
            assert_equal(r['id'], i1._id)
            title = r['highlight']['name'][0]
            assert_in(self._tagged(qs), title)
            size = len(title)
            assert_greater_equal(size, HIGHLIGHT_SIZE_TITLE)
            assert_less_equal(size, HIGHLIGHT_SIZE_TITLE + self.taglen)

    _use_migrate = False

    @enable_private_search
    def test_after_rebuild_search_for_highlight(self):
        """
        invoke rebuild_search 相当の migrate() を実行後、
        TestSearchHighlight の各テストが成功することを確認する。
        """
        my_method_name = sys._getframe().f_code.co_name
        run_test_all_after_rebuild_search(self, my_method_name,
                                          clear_index=True)

@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchSort(OsfTestCase):

    @enable_private_search
    def setUp(self):
        setup(TestSearchSort, self, create_obj=False)

    @enable_private_search
    def tearDown(self):
        tear_down(TestSearchSort, self)

    @enable_private_search
    def test_search_sort_project(self):
        """
        プロジェクトの検索結果を、更新日時、作成日時、プロジェクト名、それ
        ぞれ昇順・降順にソートできることを確認する。ソート順を指定しない場
        合、デフォルトでは更新日時の降順であることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(
                title=u'あいうえお',
                creator=u1,
                is_public=False)
            p2 = factories.ProjectFactory(
                title=u'かきくけこ',
                creator=u1,
                is_public=False)
            p3 = factories.ProjectFactory(
                title=u'さしすせそ',
                creator=u1,
                is_public=False)

        def _search(sort):
            qs = 'creator_id:' + u1._id
            return query_private_search(
                self, qs, u1, category='project', version=2, sort=sort)

        def test1():
            asc_list = ('created_asc', 'modified_asc', 'project_asc')
            for sort in asc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['title'], p1.title)
                assert_equal(results[1]['title'], p2.title)
                assert_equal(results[2]['title'], p3.title)

            # default: sort=None -> modified_desc
            desc_list = (None, 'created_desc', 'modified_desc', 'project_desc')
            for sort in desc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['title'], p3.title)
                assert_equal(results[1]['title'], p2.title)
                assert_equal(results[2]['title'], p1.title)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_search_sort_file(self):
        """
        ファイルの検索結果を、更新日時、作成日時、プロジェクト名、ファイル
        名、それぞれ昇順・降順にソートできることを確認する。ソート順を指定
        しない場合、デフォルトでは更新日時の降順であることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(
                creator=u1,
                is_public=False)
            rootdir = p1.get_addon('osfstorage').get_root()
            f1 = update_dummy_file(u1, rootdir, u'あいうえお', 1)
            f2 = update_dummy_file(u1, rootdir, u'かきくけこ', 1)
            f3 = update_dummy_file(u1, rootdir, u'さしすせそ', 1)

        def _search(sort):
            qs = 'creator_id:' + u1._id
            return query_private_search(
                self, qs, u1, category='file', version=2, sort=sort)

        def test1():
            asc_list = ('created_asc', 'modified_asc', 'project_asc', 'file_asc')
            for sort in asc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['name'], f1.name)
                assert_equal(results[1]['name'], f2.name)
                assert_equal(results[2]['name'], f3.name)

            # default: sort=None -> modified_desc
            desc_list = (None, 'created_desc', 'modified_desc', 'project_desc', 'file_desc')
            for sort in desc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['name'], f3.name)
                assert_equal(results[1]['name'], f2.name)
                assert_equal(results[2]['name'], f1.name)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_search_sort_wiki(self):
        """
        Wikiの検索結果を、更新日時、作成日時、プロジェクト名、Wikiページ名、
        それぞれ昇順・降順にソートできることを確認する。ソート順を指定しな
        い場合、デフォルトでは更新日時の降順であることを確認する。
        """
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()
            p1 = factories.ProjectFactory(
                creator=u1,
                is_public=False)
            n1 = u'あいうえお'
            n2 = u'かきくけこ'
            n3 = u'さしすせそ'
            w1 = WikiPage.objects.create_for_node(p1, n1, n1, Auth(u1))
            w2 = WikiPage.objects.create_for_node(p1, n2, n2, Auth(u1))
            w2 = WikiPage.objects.create_for_node(p1, n3, n3, Auth(u1))

        def _search(sort):
            qs = 'creator_id:' + u1._id
            return query_private_search(
                self, qs, u1, category='wiki', version=2, sort=sort)

        def test1():
            asc_list = ('created_asc', 'modified_asc', 'project_asc', 'wiki_asc')
            for sort in asc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['name'], n1)
                assert_equal(results[1]['name'], n2)
                assert_equal(results[2]['name'], n3)

            # default: sort=None -> modified_desc
            desc_list = (None, 'created_desc', 'modified_desc', 'project_desc', 'wiki_desc')
            for sort in desc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['name'], n3)
                assert_equal(results[1]['name'], n2)
                assert_equal(results[2]['name'], n1)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_search_sort_user(self):
        """
        ユーザーの検索結果を、更新日時、作成日時、ユーザー名、それぞれ昇順・
        降順にソートできることを確認する。ソート順を指定しない場合、デフォ
        ルトでは更新日時の降順であることを確認する。
        """
        with run_celery_tasks():
            n1 = u'あいうえお'
            n2 = u'かきくけこ'
            n3 = u'さしすせそ'
            u1 = factories.AuthUserFactory(fullname=n1)
            u2 = factories.AuthUserFactory(fullname=n2)
            u3 = factories.AuthUserFactory(fullname=n3)

        def _search(sort):
            qs = '*'
            return query_private_search(
                self, qs, u1, category='user', version=2, sort=sort)

        def test1():
            asc_list = ('created_asc', 'modified_asc', 'user_asc')
            for sort in asc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['user'], n1)
                assert_equal(results[1]['user'], n2)
                assert_equal(results[2]['user'], n3)

            # default: sort=None -> modified_desc
            desc_list = (None, 'created_desc', 'modified_desc', 'user_desc')
            for sort in desc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['user'], n3)
                assert_equal(results[1]['user'], n2)
                assert_equal(results[2]['user'], n1)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_search_sort_institution(self):
        """
        機関(Institution)の検索結果を、更新日時、作成日時、機関名、それぞれ
        昇順・降順にソートできることを確認する。ソート順を指定しない場合、
        デフォルトでは更新日時の降順であることを確認する。
        """
        with run_celery_tasks():
            n1 = u'あいうえお'
            n2 = u'かきくけこ'
            n3 = u'さしすせそ'
            i1 = factories.InstitutionFactory(name=n1)
            i2 = factories.InstitutionFactory(name=n2)
            i3 = factories.InstitutionFactory(name=n3)
            u1 = factories.AuthUserFactory()

        def _search(sort):
            qs = '*'
            return query_private_search(
                self, qs, u1, category='institution', version=2, sort=sort)

        def test1():
            asc_list = ('created_asc', 'modified_asc', 'institution_asc')
            for sort in asc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['name'], n1)
                assert_equal(results[1]['name'], n2)
                assert_equal(results[2]['name'], n3)

            # default: sort=None -> modified_desc
            desc_list = (None, 'created_desc', 'modified_desc', 'user_desc')
            for sort in desc_list:
                res, results = _search(sort)
                DEBUG('results', results)
                assert_equal(len(results), 3)
                assert_equal(results[0]['name'], n3)
                assert_equal(results[1]['name'], n2)
                assert_equal(results[2]['name'], n1)

        run_after_rebuild_search(self, test1)

    @enable_private_search
    def test_search_sort_unknown(self):
        with run_celery_tasks():
            u1 = factories.AuthUserFactory()

        def _search(sort):
            qs = '*'
            return query_private_search(
                self, qs, u1, version=2, sort=sort)

        unknown_list = ('unknown_asc', 'project_unknown', '__')
        for sort in unknown_list:
            res, results = _search(sort)
            expected_msg = 'unknown sort parameter: {}'.format(sort)
            assert_equal(res.status_code, 400)
            assert_equal(res.json.get('code'), 400)
            assert_equal(res.json.get('message_short'), expected_msg)
            assert_equal(res.json.get('message_long'), expected_msg)

    _use_migrate = False

    @enable_private_search
    def test_after_rebuild_search_for_sort(self):
        my_method_name = sys._getframe().f_code.co_name
        run_test_all_after_rebuild_search(self, my_method_name,
                                          clear_index=True)

@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestOriginalSearch(OsfTestCase):

    def setUp(self):
        setup(TestOriginalSearch, self)

    def tearDown(self):
        tear_down(TestOriginalSearch, self)

    def test_multilingual_unsupported(self):
        """
        ENABLE_MULTILINGUAL_SEARCH = False の場合は「本日」でも「日本」に
        マッチすることを確認する。
        """
        qs = '本日'
        res, results = query_public_search(self, qs, self.user2)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        priv_contributors = get_contributors(results, self.project_private_user2_1.title)
        pub_contributors = get_contributors(results, self.project_public_user2.title)
        tags = get_tags(results, self.project_private_user2_1.title)
        filenames = get_filenames(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('priv_contributors', priv_contributors)
        DEBUG('pub_contributors', pub_contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)

        assert_not_equal(len(results), 0)
        assert_not_equal(len(user_fullnames), 0)
        assert_not_equal(len(node_titles), 0)
        assert_equal(len(priv_contributors), 0)  # cannot access
        assert_equal(len(pub_contributors), 1)
        assert_equal(len(tags), 0)  # cannot access
        assert_equal(len(filenames), 0)  # cannot access


class TestQueryString(OsfTestCase):

    def test_split_token_with_escapable_colon(self):
        """
        バックスラッシュでコロンをエスケープして、フィールドの区切り文
        字として扱わないことの確認
        """
        self.assertEqual(quote_query_string(r'\:'), r'"\:"')
        self.assertEqual(quote_query_string(r'k*e!y\:v'), r'"k*e!y\:v"')
        self.assertEqual(quote_query_string(r'k*e!y\\\:v'), r'"k*e!y\\\:v"')

    def test_multiple_colon(self):
        """
        コロンが複数ある時、コロンで区切った最初の要素だけをクオートせ
        ずに、あとの要素全てをクオートすることを確認
        """
        self.assertEqual(quote_query_string(u'a:い:う'), u'a:"い":"う"')

    def test_capture_empty_body(self):
        """
        前置き演算子と後置き演算子のみで検索式を構成する場合に、前置き
        演算子と後置き演算子の間を空文字列の本体と認識しないことのテス
        ト。コードにバグがあると、+を+""とクオートしたり、+~を+""~とク
        オートしたりしてしまうことがある
        """
        self.assertEqual(quote_query_string(u'+'), u'+')
        self.assertEqual(quote_query_string(u'+~'), u'+~')

    def test_lazy_match_suffix(self):
        """
        前置き演算子と後置き演算子の間の部分を貪欲にマッチせず、怠惰に
        マッチすることを確認する。貪欲にマッチしてしまう場合、+あ~を+"
        あ~"とクオートしてしまう。
        """
        self.assertEqual(quote_query_string(u'+あ~'), u'+"あ"~')
        self.assertEqual(quote_query_string(u'+k:い~'), u'+k:"い"~')

    def test_adjacent_token_and_quote(self):
        """
        既にクオートでくくってある文字列の直後に何らかの文字が来るとパー
        スに失敗してしまったりするバグが無くなったことを確認
        """
        self.assertEqual(quote_query_string(u' key:"あ"'), u' key:"あ"')
        self.assertEqual(quote_query_string(u' key:"あ" '), u' key:"あ" ')
        self.assertEqual(quote_query_string(u'(key:"あ")'), u'(key:"あ")')
        self.assertEqual(quote_query_string(u'あ"い"う'), u'"あ""い""う"')

    def test_quoting_query_string(self):
        """
        様々なパターンで、クオートで囲む/囲まない処理が期待動作かを確
        認する。
        """

        # 空文字列はそのまま
        self.assertEqual(quote_query_string(u''), u'')
        # 漢字等を検索すると各文字のORと見なされてしまうので、ダブルク
        # オートで囲んで抑制
        self.assertEqual(quote_query_string(u'あいう'), u'"あいう"')
        # すでにダブルクオートで囲まれている場合は何もしない
        self.assertEqual(quote_query_string(u'"あいう"'), u'"あいう"')
        # 丸括弧は空白と同様に区切り文字と見なす
        self.assertEqual(quote_query_string(u'(あいう)'), u'("あいう")')
        # これまでの要素の合わせ技
        self.assertEqual(quote_query_string(u'("あいう")'), u'("あいう")')
        # Elasticsearchのフィールドを指定して検索する場合は、フィールド
        # と区切りのコロンをダブルクオートで囲まない
        self.assertEqual(quote_query_string(u'key:いろは'), u'key:"いろは"')
        # これまでの要素の合わせ技
        self.assertEqual(quote_query_string(u'key:(いろは)'), u'key:("いろは")')
        self.assertEqual(quote_query_string(u'key:"いろは"'), u'key:"いろは"')
        self.assertEqual(quote_query_string(u'key:("いろは")'), u'key:("いろは")')
        self.assertEqual(quote_query_string(u'(key:いろは)'), u'(key:"いろは")')
        # 二項中置き検索演算子はダブルクオートで囲まないので機能する
        self.assertEqual(quote_query_string(u'あ AND い'), u'"あ" AND "い"')
        # ワイルドカード*および?もダブルクオートで囲まないので機能する
        self.assertEqual(quote_query_string(u'*'), u'*')
        # 前置き演算子もダブルクオートで囲まないので機能する
        self.assertEqual(quote_query_string(u'+あ'), u'+"あ"')
        # これまでの要素の合わせ技(フィールド指定と前置き演算子)
        self.assertEqual(quote_query_string(u'+k:あ'), u'+k:"あ"')
        # これまでの要素の合わせ技(二項中置き演算子と括弧の複雑な組み合
        # わせ)と単項前置き演算子NOT
        self.assertEqual(
            quote_query_string(u'(あ AND (い OR う) AND (NOT え))'),
            u'("あ" AND ("い" OR "う") AND (NOT "え"))'
        )
        # バックスラッシュでひとつ後ろの文字の効用を無効にしてひとつな
        # がりの文字列(token)とみなす。バックスラッシュで次のバックスラッ
        # シュを無効にすることもできる1
        self.assertEqual(quote_query_string(r'k*e!y\\:あ'), r'k*e!y\\:"あ"')
        # 検索式としては壊れている丸括弧と二項中置き演算子の組み合わせ
        self.assertEqual(
            quote_query_string(u'あ AND () い) OR ('),
            u'"あ" AND () "い") OR ('
        )
        # フィールド区切りのエッジケース
        self.assertEqual(quote_query_string(u':いろは'), u':"いろは"')
        # バックスラッシュでひとつ後ろの文字の効用を無効にしてひとつな
        # がりの文字列(token)とみなす。バックスラッシュで次のバックスラッ
        # シュを無効にすることもできる2
        self.assertEqual(quote_query_string(r'f\(o\"o'), r'"f\(o\"o"')
        # バックスラッシュで無効にできる3
        self.assertEqual(quote_query_string(r'あ\~'), r'"あ\~"')
        # 後置き演算子は整数を伴うことができる
        self.assertEqual(quote_query_string(u'あ~1'), u'"あ"~1')
        # 後置き演算子は小数を伴うことができる
        self.assertEqual(quote_query_string(u'あ^2.4'), u'"あ"^2.4')
        # これまでの要素の合わせ技(バックスラッシュエスケープと後置き演算子)
        self.assertEqual(quote_query_string(r'あ\\~'), r'"あ\\"~')
        # ASCII英数字か*か?だけの区切りはダブルクオートで囲まない
        self.assertEqual(quote_query_string(r'ab*d'), r'ab*d')
        self.assertEqual(quote_query_string(r'a?c'), r'a?c')
        self.assertEqual(quote_query_string(r'a?c *'), r'a?c *')
        self.assertEqual(quote_query_string(r'a?c あ'), r'a?c "あ"')
        self.assertEqual(quote_query_string(r'?'), r'?')
        self.assertEqual(quote_query_string(r'123re*'), r'123re*')
        # バックスラッシュで無効にできる4 前置き演算子と後置き演算子
        self.assertEqual(quote_query_string(r'\+あ\~1'), r'"\+あ\~1"')
        # 全角空白でも区切ることができる
        self.assertEqual(quote_query_string(r'い ろ　は'), r'"い" "ろ"　"は"')
        # ワイルドカードが英数字以外を伴うときはダブルクオートで囲う
        self.assertEqual(quote_query_string(r'aあ!'), r'"aあ!"')
        self.assertEqual(quote_query_string(r'あ*う'), r'"あ*う"')
        self.assertEqual(quote_query_string(r'あい*'), r'"あい*"')
        self.assertEqual(quote_query_string(r'あい*~'), r'"あい*"~')

    def test_replace_normalized_field(self):
        """
        normalized_* に対応したフィールドに関して、検索式中の tags:
        などを normalized_tags: のように変換することを確認する。
        """

        c = convert_query_string
        for name in NORMALIZED_FIELDS:
            self.assertEqual(c(u'{}:abc'.format(name)),
                             u'normalized_{}:abc'.format(name))
            self.assertEqual(c(u'({}:abc)'.format(name)),
                             u'(normalized_{}:abc)'.format(name))
            self.assertEqual(c(u' {}:abc'.format(name)),
                             u' normalized_{}:abc'.format(name))
            self.assertEqual(c(u'normalized_{}:abc'.format(name)),
                             u'normalized_{}:abc'.format(name))
            self.assertEqual(c(u'ABC{}:abc'.format(name)),
                             u'ABC{}:abc'.format(name))

        self.assertEqual(c(u'tags:abc AND user:cde'),
            u'normalized_{}:abc AND normalized_user:cde'.format(name))
