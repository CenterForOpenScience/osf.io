import pytest

from addons.osfstorage.models import OsfStorageFile
from addons.wiki.tests.factories import NodeWikiFactory
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    CommentFactory,
    CollectionFactory,
    PrivateLinkFactory,
)
from website.settings import API_DOMAIN

@pytest.mark.django_db
class TestGuidDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self):
        return ProjectFactory()

    def test_redirects(self, app, project, user):
        #test_redirect_to_node_view
        url = '/{}guids/{}/'.format(API_BASE, project._id)
        res = app.get(url, auth=user.auth)
        redirect_url = '{}{}nodes/{}/'.format(API_DOMAIN, API_BASE, project._id)
        assert res.status_code == 302
        assert res.location == redirect_url

        #test_redirect_to_registration_view
        registration = RegistrationFactory()
        url = '/{}guids/{}/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth)
        redirect_url = '{}{}registrations/{}/'.format(API_DOMAIN, API_BASE, registration._id)
        assert res.status_code == 302
        assert res.location == redirect_url

        #test_redirect_to_collections_view
        collection = CollectionFactory()
        url = '/{}guids/{}/'.format(API_BASE, collection._id)
        res = app.get(url, auth=user.auth)
        redirect_url = '{}{}collections/{}/'.format(API_DOMAIN, API_BASE, collection._id)
        assert res.status_code == 302
        assert res.location == redirect_url

        #test_redirect_to_file_view
        test_file = OsfStorageFile.create(
            node=ProjectFactory(),
            path='/test',
            name='test',
            materialized_path='/test',
        )
        test_file.save()
        guid = test_file.get_guid(create=True)
        url = '/{}guids/{}/'.format(API_BASE, guid._id)
        res = app.get(url, auth=user.auth)
        redirect_url = '{}{}files/{}/'.format(API_DOMAIN, API_BASE, test_file._id)
        assert res.status_code == 302
        assert res.location == redirect_url

        #test_redirect_to_comment_view
        comment = CommentFactory()
        url = '/{}guids/{}/'.format(API_BASE, comment._id)
        res = app.get(url, auth=user.auth)
        redirect_url = '{}{}comments/{}/'.format(API_DOMAIN, API_BASE, comment._id)
        assert res.status_code == 302
        assert res.location == redirect_url

        #test_redirect_throws_404_for_invalid_guids
        url = '/{}guids/{}/'.format(API_BASE, 'fakeguid')
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_redirects_through_view_only_link(self, app, project, user):

        #test_redirect_when_viewing_private_project_through_view_only_link
        view_only_link = PrivateLinkFactory(anonymous=False)
        view_only_link.nodes.add(project)
        view_only_link.save()

        url = '/{}guids/{}/?view_only={}'.format(API_BASE, project._id, view_only_link.key)
        res = app.get(url, auth=user.auth)
        redirect_url = '{}{}nodes/{}/?view_only={}'.format(API_DOMAIN, API_BASE, project._id, view_only_link.key)
        assert res.status_code == 302
        assert res.location == redirect_url

        #test_redirect_when_viewing_private_project_file_through_view_only_link
        test_file = OsfStorageFile.create(
            node=project,
            path='/test',
            name='test',
            materialized_path='/test',
        )
        test_file.save()
        guid = test_file.get_guid(create=True)
        url = '/{}guids/{}/?view_only={}'.format(API_BASE, guid._id, view_only_link.key)
        res = app.get(url, auth=user.auth)
        redirect_url = '{}{}files/{}/?view_only={}'.format(API_DOMAIN, API_BASE, test_file._id, view_only_link.key)
        assert res.status_code == 302
        assert res.location == redirect_url

        #test_redirect_when_viewing_private_project_comment_through_view_only_link
        comment = CommentFactory(node=project)
        url = '/{}guids/{}/?view_only={}'.format(API_BASE, comment._id, view_only_link.key)
        res = app.get(url, auth=AuthUserFactory().auth)
        redirect_url = '{}{}comments/{}/?view_only={}'.format(API_DOMAIN, API_BASE, comment._id, view_only_link.key)
        assert res.status_code == 302
        assert res.location == redirect_url

    def test_resolves(self, app, project, user):
        #test_resolve_query_param
        url = '{}{}guids/{}/?resolve=false'.format(API_DOMAIN, API_BASE, project._id)
        res = app.get(url, auth=user.auth)
        related_url = '{}{}nodes/{}/'.format(API_DOMAIN, API_BASE, project._id)
        related = res.json['data']['relationships']['referent']['links']['related']
        assert related['href'] == related_url
        assert related['meta']['type'] == 'nodes'

        #test_referent_is_embeddable
        project = ProjectFactory(creator=user)
        url = '{}{}guids/{}/?resolve=false&embed=referent'.format(API_DOMAIN, API_BASE, project._id)
        res = app.get(url, auth=user.auth)
        related_url = '{}{}nodes/{}/'.format(API_DOMAIN, API_BASE, project._id)
        related = res.json['data']['relationships']['referent']['links']['related']
        assert related['href'] == related_url
        assert related['meta']['type'] == 'nodes'
        referent = res.json['data']['embeds']['referent']['data']
        assert referent['id'] == project._id
        assert referent['type'] == 'nodes'
