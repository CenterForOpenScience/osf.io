# -*- coding: utf-8 -*-
from __future__ import print_function

import functools

import mock
import pytest
from nose.tools import *  # noqa: F403

from framework.auth.core import Auth
from osf_tests import factories
from tests.base import OsfTestCase
from website.util import web_url_for, api_url_for
from website.views import find_bookmark_collection

from website.search.util import quote_query_string

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
        'size': 10
    }


def build_private_search_query(query_string):
    return {
        'api_version': {
            'version': 1,
            'vendor': 'grdm'
        },
        'elasticsearch_dsl': build_query(query_string)
    }

def DEBUG(name, obj):
    if ENABLE_DEBUG:
        import sys
        print('{}:\n{}'.format(name, se(u2s(obj))), file=sys.stderr)


# XXX FIXME: Python3では全てをUnicodeとして扱う
def s2u(obj):
    if isinstance(obj, str):
        return obj.decode('utf-8')
    if isinstance(obj, list):
        return [s2u(s) for s in obj]
    if isinstance(obj, dict):
        return {s2u(key): s2u(val) for key, val in obj.iteritems()}
    return obj

def u2s(obj):
    if isinstance(obj, unicode):
        return obj.encode('utf-8')
    if isinstance(obj, list):
        return [u2s(s) for s in obj]
    if isinstance(obj, dict):
        return {u2s(key): u2s(val) for key, val in obj.iteritems()}
    return obj

# string-escape
def se(listordict):
    return str(listordict).decode('string-escape')

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

def get_user_fullnames(results):
    return [r['names']['fullname'] for r in results if r['category'] == 'user']

def get_filenames(results):
    return [r['name'] for r in results if r['category'] == 'file']

def get_node_titles(results):
    return [r['title'] for r in results if r['category'] in
            ['project', 'component', 'registration', 'preprint']]

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

# see osf_tests/test_search_view.py
@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearch(OsfTestCase):

    @enable_private_search
    def setUp(self):
        super(TestSearch, self).setUp()
        import website.search.search as search
        search.delete_all()

        from tests.utils import run_celery_tasks
        with run_celery_tasks():
            self.user1 = factories.AuthUserFactory(fullname='日本語ユーザー1')
            self.user2 = factories.AuthUserFactory(fullname='日本語ユーザー2')
            self.user3 = factories.AuthUserFactory(
                fullname=u'\u304b\u3099')  # か+濁点
            self.user4 = factories.AuthUserFactory(
                fullname=u'\u304e')  # ぎ

            self.project_private_user1 = factories.ProjectFactory(title='private日本語プロジェクト1', creator=self.user1, is_public=False)
            self.project_private_user2_1 = factories.ProjectFactory(title='private日本語プロジェクト2_1', creator=self.user2, is_public=False)
            self.project_private_user2_2 = factories.ProjectFactory(title='private日本語プロジェクト2_2', creator=self.user2, is_public=False)

            self.project_public_user1 = factories.ProjectFactory(title='public日本語プロジェクト1', creator=self.user1, is_public=True)
            self.project_public_user2 = factories.ProjectFactory(title='public日本語プロジェクト2', creator=self.user2, is_public=True)

            # private file
            rootdir = self.project_private_user1.get_addon('osfstorage').get_root()
            rootdir.append_file(u'日本語ファイル名.txt')
            self.project_private_user1.add_tag(u'日本語タグ',
                                               Auth(self.user1),
                                               save=True)

    @enable_private_search
    def tearDown(self):
        super(TestSearch, self).tearDown()
        import website.search.search as search
        search.delete_all()

    def query_private_search(self, qs, user):
        res = self.app.post_json(
            api_url_for('search_search'),
            build_private_search_query(qs),
            auth=user.auth
        )
        return res, res.json.get('results')

    def query_public_search(self, qs, user):
        res = self.app.post_json(
            api_url_for('search_search'),
            build_query(qs),
            auth=user.auth
        )
        return res, res.json.get('results')

    def query_search_contributor(self, qs, user):
        res = self.app.get(
            api_url_for('search_contributor'),
            {'query': qs, 'page': 0, 'size': 10},
        )
        DEBUG('query_search_contributor', res)
        return res, res.json.get('users')

    @enable_private_search
    def test_private_search_user1(self):
        """
        user1 がアクセス可能なプロジェクトに関するデータを検索できるこ
        とを確認する。
        プライベートなプロジェクトに所属するタグとファイル名が有る場合。
        """
        qs = '日本語'
        res, results = self.query_private_search(qs, self.user1)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user1.title)
        tags = get_tags(results, self.project_private_user1.title)
        filenames = get_filenames(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)

        assert_equal(len(results), 6)  # user=2, project=3, file=1
        assert_equal(len(user_fullnames), 2)
        assert_equal(len(node_titles), 3)  # private=1, public=2
        assert_equal(len(contributors), 1)
        assert_equal(len(tags), 1)
        assert_equal(len(filenames), 1)
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
        res, results = self.query_private_search(qs, self.user2)
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
            s2u(self.project_private_user1.title),
            s2u(node_titles)
        )
        assert_not_in(
            s2u(self.user1.fullname),
            s2u(contributors)
        )

    def test_disable_multilingual(self):
        """
        ENABLE_MULTILINGUAL_SEARCH = False の場合は「本日」でも「日本」に
        マッチすることを確認する。
        """
        qs = '本日'
        res, results = self.query_public_search(qs, self.user2)
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

        assert_not_equal(len(results), 0)
        assert_not_equal(len(user_fullnames), 0)
        assert_not_equal(len(node_titles), 0)
        assert_not_equal(len(contributors), 0)
        #assert_equal(len(tags), 0)
        assert_not_equal(len(filenames), 0)

    @enable_private_search
    def test_no_match(self):
        """
        「本日」は「日本」にマッチしないことを確認する。
        """
        qs = '本日'
        res, results = self.query_private_search(qs, self.user2)
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
        AND 式も使用して、タグ名に含まれる文字をさらに限定している。
        """
        qs = 'tags:("日本語") AND タグ'
        res, results = self.query_private_search(qs, self.user1)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user1.title)
        tags = get_tags(results, self.project_private_user1.title)
        filenames = get_filenames(results)

        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        DEBUG('node_titles', node_titles)
        DEBUG('contributors', contributors)
        DEBUG('tags', tags)
        DEBUG('filenames', filenames)

        assert_equal(len(results), 1)
        assert_equal(len(user_fullnames), 0)
        assert_equal(len(node_titles), 1)  # private=2, public=2
        assert_equal(len(contributors), 1)
        assert_equal(len(tags), 1)
        assert_equal(len(filenames), 0)

    @enable_private_search
    def test_file(self):
        """
        ファイル名を検索できることを確認する。
        AND 式も使用して、ファイル名に含まれる文字をさらに限定している。
        """
        qs = 'category:file && 日本語'
        res, results = self.query_private_search(qs, self.user1)
        user_fullnames = get_user_fullnames(results)
        node_titles = get_node_titles(results)
        contributors = get_contributors(results, self.project_private_user1.title)
        tags = get_tags(results, self.project_private_user1.title)
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
    def _common_normalize_contributor(self, qs):
        # app.get() の場合は str にしなければならない。
        res, results = self.query_search_contributor(qs, self.user1)

        # get_user_fullnames() cannot be used here.
        user_fullnames = [r['fullname'] for r in results]
        DEBUG('results', results)
        DEBUG('user_fullnames', user_fullnames)
        assert_equal(len(results), 1)
        assert_equal(len(user_fullnames), 1)

    def test_normalize_contributor1(self):
        """
        Unicode正規化のテスト。
        データベースに登録されている濁点付き文字が結合可能濁点と母体の
        文字の組み合わせで表現されている場合に、合成済み文字で検索でき
        ることを確認する。
        Add Contributorsにおける検索のみ、正規化の効果がある。
        """
        qs = u2s(u'\u304c')  # が
        self._common_normalize_contributor(qs)

    def test_normalize_contributor2(self):
        """
        Unicode正規化のテスト。
        データベースに登録されている濁点付き文字が合成済み文字の場合に、
        結合可能濁点と母体の文字の組み合わせで検索できることを確認する。
        Add Contributorsにおける検索のみ、正規化の効果がある。
        """
        # app.get() の場合は str にしなければならないようだ。
        qs = u2s(u'\u304d\u3099')  # き+濁点
        self._common_normalize_contributor(qs)

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
        bad_request(build_invalid_query1(qs, 2, 'grdm'))
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


class TestQuotingQueryString(OsfTestCase):

    def test_split_token_with_escapable_colon(self):
        """
        バックスラッシュでコロンをエスケープして、フィールドの区切り文
        字として扱わないことの確認
        """
        self.assertEqual(quote_query_string(ur'\:'), ur'"\:"')
        self.assertEqual(quote_query_string(ur'k*e!y\:v'), ur'"k*e!y\:v"')
        self.assertEqual(quote_query_string(ur'k*e!y\\\:v'), ur'"k*e!y\\\:v"')

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
        self.assertEqual(quote_query_string(ur'k*e!y\\:あ'), ur'k*e!y\\:"あ"')
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
        self.assertEqual(quote_query_string(ur'f\(o\"o'), ur'"f\(o\"o"')
        # バックスラッシュで無効にできる3
        self.assertEqual(quote_query_string(ur'あ\~'), ur'"あ\~"')
        # 後置き演算子は整数を伴うことができる
        self.assertEqual(quote_query_string(u'あ~1'), u'"あ"~1')
        # 後置き演算子は小数を伴うことができる
        self.assertEqual(quote_query_string(u'あ^2.4'), u'"あ"^2.4')
        # これまでの要素の合わせ技(バックスラッシュエスケープと後置き演算子)
        self.assertEqual(quote_query_string(ur'あ\\~'), ur'"あ\\"~')
        # ASCII英数字か*か?だけの区切りはダブルクオートで囲まない
        self.assertEqual(quote_query_string(ur'ab*d'), ur'ab*d')
        self.assertEqual(quote_query_string(ur'a?c'), ur'a?c')
        self.assertEqual(quote_query_string(ur'a?c *'), ur'a?c *')
        self.assertEqual(quote_query_string(ur'a?c あ'), ur'a?c "あ"')
        self.assertEqual(quote_query_string(ur'?'), ur'?')
        self.assertEqual(quote_query_string(ur'123re*'), ur'123re*')
        # バックスラッシュで無効にできる4 前置き演算子と後置き演算子
        self.assertEqual(quote_query_string(ur'\+あ\~1'), ur'"\+あ\~1"')
        # 全角空白でも区切ることができる
        self.assertEqual(quote_query_string(ur'い ろ　は'), ur'"い" "ろ"　"は"')
        # ワイルドカードが英数字以外を伴うときはダブルクオートで囲う
        self.assertEqual(quote_query_string(ur'aあ!'), ur'"aあ!"')
        self.assertEqual(quote_query_string(ur'あ*う'), ur'"あ*う"')
        self.assertEqual(quote_query_string(ur'あい*'), ur'"あい*"')
        self.assertEqual(quote_query_string(ur'あい*~'), ur'"あい*"~')
