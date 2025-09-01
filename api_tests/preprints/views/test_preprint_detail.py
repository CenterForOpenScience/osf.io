import pytest

from django.utils import timezone

from api.base.settings.defaults import API_BASE
from osf.utils.permissions import WRITE, ADMIN
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    ProjectFactory,
    SubjectFactory,
    PreprintProviderFactory,
    InstitutionFactory
)


def build_preprint_update_payload(
        node_id, attributes=None, relationships=None,
        jsonapi_type='preprints'):
    payload = {
        'data': {
            'id': node_id,
            'type': jsonapi_type,
            'attributes': attributes,
            'relationships': relationships
        }
    }
    return payload


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestPreprintDetail:

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def preprint_pre_mod(self, user):
        return PreprintFactory(reviews_workflow='pre-moderation', is_published=False, creator=user)

    @pytest.fixture()
    def moderator(self, preprint_pre_mod):
        mod = AuthUserFactory()
        preprint_pre_mod.provider.get_group('moderator').user_set.add(mod)
        return mod

    @pytest.fixture()
    def unpublished_preprint(self, user):
        return PreprintFactory(creator=user, is_published=False)

    @pytest.fixture()
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/'

    @pytest.fixture()
    def unpublished_url(self, unpublished_preprint):
        return f'/{API_BASE}preprints/{unpublished_preprint._id}/'

    @pytest.fixture()
    def versions_url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/versions/'

    @pytest.fixture()
    def res(self, app, url):
        return app.get(url)

    @pytest.fixture()
    def data(self, res):
        return res.json['data']

    def test_preprint_detail(self, app, user, preprint, url, versions_url, res, data):
        #   test_preprint_detail_success
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

        #   test_preprint_top_level
        assert data['type'] == 'preprints'
        assert data['id'] == preprint._id

        #   test title in preprint data
        assert data['attributes']['title'] == preprint.title

        #   test contributors in preprint data
        assert data['relationships'].get('contributors', None)
        assert data['relationships']['contributors'].get('data', None) is None

        #   test no node attached to preprint
        assert data['relationships']['node'].get('data', None) is None

        #  test versions in relationships
        assert data['relationships']['versions']['links']['related']['href'].endswith(versions_url)

        #   test_preprint_node_deleted doesn't affect preprint
        deleted_node = ProjectFactory(creator=user, is_deleted=True)
        deleted_preprint = PreprintFactory(project=deleted_node, creator=user)

        deleted_preprint_res = app.get(
            f'/{API_BASE}preprints/{deleted_preprint._id}/',
            expect_errors=True
        )
        assert deleted_preprint_res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

        #  test node relationship exists when attached to preprint
        node = ProjectFactory(creator=user)
        preprint_with_node = PreprintFactory(project=node, creator=user)
        preprint_with_node_res = app.get(f'/{API_BASE}preprints/{preprint_with_node._id}/')

        node_data = preprint_with_node_res.json['data']['relationships']['node']['data']

        assert node_data.get('id', None) == preprint_with_node.node._id
        assert node_data.get('type', None) == 'nodes'

    def test_withdrawn_preprint(self, app, user, moderator, preprint_pre_mod):
        # test_retracted_fields
        url = f'/{API_BASE}preprints/{preprint_pre_mod._id}/'
        preprint_pre_mod.add_contributor(user, ADMIN)
        res = app.get(url, auth=user.auth)
        data = res.json['data']

        assert not data['attributes']['date_withdrawn']
        assert 'withdrawal_justification' not in data['attributes']
        assert 'ever_public' not in data['attributes']

        ## retracted and not ever_public
        assert not preprint_pre_mod.ever_public
        preprint_pre_mod.date_withdrawn = timezone.now()
        preprint_pre_mod.withdrawal_justification = 'assumptions no longer apply'
        preprint_pre_mod.save()
        assert preprint_pre_mod.is_retracted
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        # moderator can't see preprint with initial machine state. see test_moderator_does_not_see_initial_preprint
        res = app.get(url, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 404

        ## retracted and ever_public (True)
        preprint_pre_mod.ever_public = True
        preprint_pre_mod.save()
        res = app.get(url, auth=user.auth)
        data = res.json['data']
        assert data['attributes']['date_withdrawn']
        assert 'withdrawal_justification' in data['attributes']
        assert 'assumptions no longer apply' == data['attributes']['withdrawal_justification']
        assert 'date_withdrawn' in data['attributes']

    def test_embed_contributors(self, app, user, preprint):
        url = '/{}preprints/{}/?embed=contributors'.format(
            API_BASE, preprint._id)

        res = app.get(url, auth=user.auth)
        embeds = res.json['data']['embeds']
        ids = preprint.contributors.all().values_list('guids___id', flat=True)
        ids = [f'{preprint._id}-{id_}' for id_ in ids]
        for contrib in embeds['contributors']['data']:
            assert contrib['id'] in ids

    def test_return_affiliated_institutions(self, app, user, preprint, institution, url):
        """
        Confirmation test for the the new preprint affiliated institutions feature
        """
        preprint.affiliated_institutions.add(institution)
        res = app.get(url)
        assert res.status_code == 200
        relationship_link = res.json['data']['relationships']['affiliated_institutions']['links']['related']['href']
        assert f'/v2/preprints/{preprint._id}/institutions/' in relationship_link
        relationship_link = res.json['data']['relationships']['affiliated_institutions']['links']['self']['href']
        assert f'/v2/preprints/{preprint._id}/relationships/institutions/' in relationship_link


@pytest.mark.django_db
class TestPreprintDelete:

    @pytest.fixture()
    def unpublished_preprint(self, user):
        return PreprintFactory(creator=user, is_published=False)

    @pytest.fixture()
    def published_preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def url(self, user):
        return f'/{API_BASE}preprints/{{}}/'

    def test_can_delete_draft_preprints(
        self, app, user, url, unpublished_preprint
    ):

        url = f'/{API_BASE}preprints/{unpublished_preprint._id}/'
        res = app.delete(url, auth=user.auth)
        assert res.status_code == 204

        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_cannot_delete_published_preprints(self, app, user, url, published_preprint):
        url = f'/{API_BASE}preprints/{published_preprint._id}/'

        res = app.delete(url, auth=user.auth, expect_errors=True)
        assert res.json['errors'][0]['detail'] == 'You cannot delete created preprint'
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

    def test_cannot_delete_in_moderation_preprints(self, app, user, url):
        pre_moderation_preprint = PreprintFactory(creator=user, reviews_workflow='pre-moderation')
        post_moderation_preprint = PreprintFactory(creator=user, reviews_workflow='post-moderation')

        url = f'/{API_BASE}preprints/{pre_moderation_preprint._id}/'
        res = app.delete(url, auth=user.auth, expect_errors=True)
        assert res.json['errors'][0]['detail'] == 'You cannot delete created preprint'
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        url = f'/{API_BASE}preprints/{post_moderation_preprint._id}/'

        res = app.delete(url, auth=user.auth, expect_errors=True)
        assert res.json['errors'][0]['detail'] == 'You cannot delete created preprint'
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200


@pytest.mark.django_db
class TestPreprintDetailPermissions:

    @pytest.fixture()
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project(self, admin):
        return ProjectFactory(creator=admin, is_public=True)

    @pytest.fixture()
    def private_project(self, admin):
        return ProjectFactory(creator=admin, is_public=False)

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def unpublished_preprint(self, admin, provider, subject, public_project):
        fact = PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            is_published=False,
            machine_state='initial')
        assert fact.is_published is False
        return fact

    @pytest.fixture()
    def private_preprint(self, admin, provider, subject, private_project, write_contrib):
        fact = PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            is_published=True,
            is_public=False,
            machine_state='accepted')
        fact.add_contributor(write_contrib, permissions=WRITE)
        fact.is_public = False
        fact.save()
        return fact

    @pytest.fixture()
    def published_preprint(self, admin, provider, subject, write_contrib):
        fact = PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            is_published=True,
            is_public=True,
            machine_state='accepted')
        fact.add_contributor(write_contrib, permissions=WRITE)
        return fact

    @pytest.fixture()
    def abandoned_private_preprint(
            self, admin, provider, subject, private_project):
        return PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            project=private_project,
            is_published=False,
            is_public=False,
            machine_state='initial')

    @pytest.fixture()
    def abandoned_public_preprint(
            self, admin, provider, subject, public_project):
        fact = PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            project=public_project,
            is_published=False,
            is_public=True,
            machine_state='initial')
        assert fact.is_public is True
        return fact

    @pytest.fixture()
    def abandoned_private_url(self, abandoned_private_preprint):
        return '/{}preprints/{}/'.format(
            API_BASE, abandoned_private_preprint._id)

    @pytest.fixture()
    def abandoned_public_url(self, abandoned_public_preprint):
        return '/{}preprints/{}/'.format(
            API_BASE, abandoned_public_preprint._id)

    @pytest.fixture()
    def unpublished_url(self, unpublished_preprint):
        return f'/{API_BASE}preprints/{unpublished_preprint._id}/'

    @pytest.fixture()
    def private_url(self, private_preprint):
        return f'/{API_BASE}preprints/{private_preprint._id}/'

    def test_preprint_is_published_detail(
            self, app, admin, write_contrib, non_contrib,
            unpublished_preprint, unpublished_url):

        #   test_unpublished_visible_to_admins
        res = app.get(unpublished_url, auth=admin.auth)
        assert res.json['data']['id'] == unpublished_preprint._id

    #   test_unpublished_invisible_to_write_contribs
        res = app.get(
            unpublished_url,
            auth=write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unpublished_invisible_to_non_contribs
        res = app.get(
            unpublished_url,
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unpublished_invisible_to_public
        res = app.get(unpublished_url, expect_errors=True)
        assert res.status_code == 401

    def test_preprint_is_public_detail(
            self, app, admin, write_contrib, non_contrib,
            private_preprint, private_url):

        #   test_private_visible_to_admins
        res = app.get(private_url, auth=admin.auth)
        assert res.json['data']['id'] == private_preprint._id

    #   test_private_visible_to_write_contribs
        res = app.get(private_url, auth=write_contrib.auth)
        assert res.status_code == 200

    #   test_private_invisible_to_non_contribs
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_private_invisible_to_public
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401

    def test_preprint_is_abandoned_detail(
            self, app, admin, write_contrib,
            non_contrib, abandoned_private_preprint,
            abandoned_public_preprint,
            abandoned_private_url,
            abandoned_public_url):

        #   test_abandoned_private_visible_to_admins
        res = app.get(abandoned_private_url, auth=admin.auth)
        assert res.json['data']['id'] == abandoned_private_preprint._id

    #   test_abandoned_private_invisible_to_write_contribs
        res = app.get(
            abandoned_private_url,
            auth=write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_abandoned_private_invisible_to_non_contribs
        res = app.get(
            abandoned_private_url,
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_abandoned_private_invisible_to_public
        res = app.get(abandoned_private_url, expect_errors=True)
        assert res.status_code == 401

    #   test_abandoned_public_visible_to_admins
        res = app.get(abandoned_public_url, auth=admin.auth)
        assert res.json['data']['id'] == abandoned_public_preprint._id

    #   test_abandoned_public_invisible_to_write_contribs
        res = app.get(
            abandoned_public_url,
            auth=write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_abandoned_public_invisible_to_non_contribs
        res = app.get(
            abandoned_public_url,
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_abandoned_public_invisible_to_public
        res = app.get(abandoned_public_url, expect_errors=True)
        assert res.status_code == 401

    def test_access_primary_file_on_unpublished_preprint(
            self, app, user, write_contrib):
        unpublished = PreprintFactory(creator=user, is_public=True, is_published=False)
        preprint_file_id = unpublished.primary_file._id
        url = f'/{API_BASE}files/{preprint_file_id}/'

        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        assert unpublished.is_published is False
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        unpublished.add_contributor(write_contrib, permissions=WRITE, save=True)
        res = app.get(url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
