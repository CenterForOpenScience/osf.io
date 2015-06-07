import os
import shutil
import mock

from nose.tools import *
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory
from tests.test_features import requires_celery

from website.util import web_url_for, api_url_for
from website.static_snapshot.decorators import cache
from website.static_snapshot.utils import get_path
from website import settings


@requires_celery
class TestDecorator(OsfTestCase):

    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.seo_path = 'website/seocache'
        self.project = ProjectFactory(is_public=True)
        self.project_url = self.project.web_url_for('view_project')
        self.homepage_url = web_url_for('index')
        self.PROJECT_PAGES = ['project', 'files', 'wiki', 'statistics', 'registrations', 'forks']

    def test_index_page_calls_snapshot_decorator(self):
        # Clear cache files
        if not cache.get('index') == 'pending':
            cache.clear()
        res = self.app.get(self.homepage_url)
        if cache.get('cached_content'):
            current_path = os.path.join(self.seo_path, 'index')
            shutil.rmtree(current_path)

        assert_equal(res.status_code,  200)
        assert_equal(cache.get('current_page'), 'index')

    def test_project_page_calls_snapshot_decorator(self):
        page_url = {
            'project': 'view_project',
            'files': 'collect_file_trees',
            'wiki': 'project_wiki_home',
            'statistics': 'project_statistics',
            'registrations': 'node_registrations',
            'forks': 'node_forks'
        }
        for page_name in self.PROJECT_PAGES:
            # Clear cache files
            if not cache.get(page_name) == 'pending':
                cache.clear()

            url = self.project.web_url_for(page_url[page_name])
            res = self.app.get(url)
            if cache.get('cached_content'):  # Clear the path, if created before
                current_path = os.path.join(self.seo_path, 'node', self.project._primary_key, page_name)
                shutil.rmtree(current_path)
                res = self.app.get(url)
            assert_true(res.status_code in [200, 302])
            assert_equal(cache.get('current_page'), page_name)

    def test_profile_page_calls_snapshot_decorator(self):
        user = UserFactory()
        url = web_url_for('profile_view_id', uid=user._id)
        res = self.app.get(url)
        if cache.get('cached_content'):
                current_path = os.path.join(self.seo_path, 'user', user._primary_key, 'profile')
                shutil.rmtree(current_path)
                res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(cache.get('current_page'), 'profile')

    def test_private_project_does_not_returns_static_snapshot(self):
        cache.set('current_page', 'project')
        project = ProjectFactory(is_public=False)
        url = project.web_url_for('view_project')
        self.app.get(url)
        # Private projects should clear cache
        assert_false(cache.get('current_page'))

@requires_celery
class TestUtils(OsfTestCase):

    def setUp(self):
        super(OsfTestCase, self).setUp()

    def test_get_path_for_non_index_page_returns_correct_paths(self):
        fake_page_name = 'fake_page'
        fake_id = 'fake_id'
        fake_category = 'fake_category'
        res = get_path(fake_page_name, fake_id, fake_category)
        expected_path = os.path.join(settings.SEO_CACHE_PATH, fake_category, fake_id) + '/'
        expected_full_path = os.path.join(settings.SEO_CACHE_PATH, fake_category, fake_id, fake_page_name) + '.html'

        assert_equal(res['path'], expected_path)
        assert_equal(res['full_path'], expected_full_path)

    def test_get_path_for_index_page_returns_correct_paths(self):
        page_name = 'index'
        res = get_path(page_name)
        expected_path = os.path.join(settings.SEO_CACHE_PATH) + '/'
        expected_full_path = os.path.join(settings.SEO_CACHE_PATH, page_name) + '.html'

        assert_equal(res['path'], expected_path)
        assert_equal(res['full_path'], expected_full_path)

@requires_celery
class TestViews(OsfTestCase):

    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.seo_path = 'website/seocache'
        self.project = ProjectFactory(is_public=True)
        self.PROJECT_PAGES = ['project', 'files', 'wiki', 'statistics', 'registrations', 'forks']

    @mock.patch('website.static_snapshot.views.tasks.get_static_snapshot')
    def test_get_static_snapshot_creates_cache_for_node(self, mock_result):
        mock_task = mock.Mock()
        mock_result.AsyncResult.return_value = mock_task
        mock_task.id = 'mock_task_id'
        mock_task.state = 'SUCCESS'

        for page_name in self.PROJECT_PAGES:
            current_path = os.path.join(self.seo_path, 'node', self.project._primary_key, page_name)
            if os.path.exists(current_path):
                shutil.rmtree(current_path)
            mock_task.result = {
                'content': '<html><head><body> fake project content </body></head></html>',
                'path': current_path.replace(page_name, '', 1)
                }
            cache.set('current_page', page_name)

            url = self.project.api_url_for('view_project', _='fake_google_bot_crawler_request')
            print url
            res = self.app.get(url)
            cache_created_at = os.path.join(self.seo_path, 'node', self.project._primary_key, page_name) + '.html'
            assert_true(res.status_code in [200, 302])
            assert_true(os.path.exists(cache_created_at))
            assert_false(cache.get('current_page'))


    @mock.patch('website.static_snapshot.views.tasks.get_static_snapshot')
    def test_get_static_snapshot_creates_cache_for_user(self, mock_result):
        mock_task = mock.Mock()
        mock_result.AsyncResult.return_value = mock_task
        mock_task.id = 'mock_task_id'
        mock_task.state = 'SUCCESS'

        user = UserFactory()
        current_path = os.path.join(self.seo_path, 'user', user._id, 'profile')
        if os.path.exists(current_path):
            shutil.rmtree(current_path)
        mock_task.result = {
            'content': '<html><head><body> fake user content </body></head></html>',
            'path': current_path.replace('profile', '', 1)
        }
        cache.set('current_page', 'profile')

        url = api_url_for('serialize_social', uid=user._id, _='fake_google_bot_crawler_request')
        res = self.app.get(url)
        cache_created_at = os.path.join(self.seo_path, 'user', user._id, 'profile') + '.html'
        assert_equal(res.status_code, 200)
        assert_true(os.path.exists(cache_created_at))


    @mock.patch('website.static_snapshot.views.tasks.get_static_snapshot')
    def test_get_static_snapshot_creates_cache_for_index_page(self, mock_result):
        mock_task = mock.Mock()
        mock_result.AsyncResult.return_value = mock_task
        mock_task.id = 'mock_task_id'
        mock_task.state = 'SUCCESS'

        current_path = os.path.join(self.seo_path, 'index')
        if os.path.exists(current_path):
            shutil.rmtree(current_path)
        mock_task.result = {
            'content': '<html><head><body> fake index page content </body></head></html>',
            'path': settings.SEO_CACHE_PATH
        }
        cache.set('current_page', 'index')

        url = api_url_for('homepage_snapshot', _='fake_google_bot_crawler_request')
        res = self.app.get(url)
        cache_created_at = os.path.join(self.seo_path, 'index') + '.html'
        assert_equal(res.status_code, 200)
        assert_true(os.path.exists(cache_created_at))



