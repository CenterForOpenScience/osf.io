import pytest
from django.utils import timezone

from api.base.settings.defaults import API_BASE
from osf.models import Outcome
from osf.utils.outcomes import ArtifactTypes
from osf_tests.factories import (
    AuthUserFactory,
    IdentifierFactory,
    ProjectFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
)


REGISTRATION_LIST_ROUTES = [
    f'/{API_BASE}registrations/',
    f'/{API_BASE}nodes/{{node_id}}/registrations/',
    f'/{API_BASE}users/{{user_id}}/registrations/',
    f'/{API_BASE}providers/registrations/{{provider_id}}/registrations/',
]

@pytest.mark.django_db
class TestRegistrationDetailOpenPracticeAnnotations:

    @pytest.fixture
    def registration(self):
        return RegistrationFactory(is_public=True, has_doi=True)

    @pytest.fixture
    def outcome(self, registration):
        return Outcome.objects.for_registration(registration, create=True)

    @pytest.fixture
    def data_resource(self, outcome):
        return outcome.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.DATA,
            finalized=True
        )

    @pytest.fixture
    def code_resource(self, outcome):
        return outcome.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.ANALYTIC_CODE,
            finalized=False,
        )

    @pytest.fixture
    def materials_resource(self, outcome):
        return outcome.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.MATERIALS,
            finalized=True,
            deleted=timezone.now()
        )

    @pytest.fixture()
    def url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/'

    @pytest.mark.parametrize('resource_type', ArtifactTypes.public_types())
    def test_badge_annotations(self, app, registration, outcome, url, resource_type):
        outcome.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=resource_type,
            finalized=True,
        )

        resp = app.get(url, auth=None, expect_errors=False)
        attributes = resp.json['data']['attributes']

        badge_attribute = f'has_{resource_type.name.lower()}'
        assert attributes[badge_attribute]

    def test_badge_annotations_exclude_nonvisible_results(
        self, app, registration, data_resource, code_resource, materials_resource, url
    ):
        code_resource.finalized = False
        code_resource.save()
        materials_resource.deleted = timezone.now()
        materials_resource.save()

        resp = app.get(url, auth=None, expect_errors=False)
        attributes = resp.json['data']['attributes']

        assert attributes['has_data']
        # Not finalized
        assert not attributes['has_analytic_code']
        # Deleted
        assert not attributes['has_materials']
        # Do not exist
        assert not attributes['has_papers']
        assert not attributes['has_supplements']

    def test_registration_does_not_inherit_badges_from_primary_resource(self, app, registration, outcome, data_resource):
        artifact_registration = RegistrationFactory(is_public=True, has_doi=True)
        artifact_doi = artifact_registration.get_identifier('doi')
        outcome.artifact_metadata.create(
            identifier=artifact_doi, artifact_type=ArtifactTypes.ANALYTIC_CODE, finalized=True
        )

        resp = app.get(f'/{API_BASE}registrations/{artifact_registration._id}/', auth=None)
        attributes = resp.json['data']['attributes']

        assert not attributes['has_data']  # Does not have the data badge from the primary resource
        assert not attributes['has_analytic_code']  # Does not have the code badge it provides to the primary resource

    def test_primary_resource_does_not_inherit_badges_from_sub_resource(Self, app, registration, data_resource):
        new_primary_resource = RegistrationFactory(is_public=True, has_doi=True)
        new_outcome = Outcome.objects.for_registration(new_primary_resource, create=True)
        sub_resource_doi = registration.get_identifier('doi')
        new_outcome.artifact_metadata.create(
            identifier=sub_resource_doi, artifact_type=ArtifactTypes.MATERIALS, finalized=True
        )

        resp = app.get(f'/{API_BASE}registrations/{new_primary_resource._id}/', auth=None)
        attributes = resp.json['data']['attributes']

        assert attributes['has_materials']   # Does have badge for the added artifact
        assert not attributes['has_data']  # Does not have badge from the artifact's outcome


@pytest.mark.django_db
class TestRegistrationListOpenPracticeAnnotations:

    @pytest.fixture
    def creator(self):
        return AuthUserFactory()

    @pytest.fixture
    def project(self, creator):
        return ProjectFactory(creator=creator)

    @pytest.fixture
    def provider(self, creator):
        provider = RegistrationProviderFactory()
        provider.update_group_permissions()
        provider.get_group('moderator').user_set.add(creator)
        return provider

    @pytest.fixture(autouse=True)
    def open_data(self, project, provider, creator):
        r = RegistrationFactory(
            project=project,
            provider=provider,
            creator=creator,
            is_public=True,
            has_doi=True
        )
        o = Outcome.objects.for_registration(r, create=True)
        o.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.DATA,
            finalized=True,
        )
        return r

    @pytest.fixture(autouse=True)
    def open_code(self, project, provider, creator):
        r = RegistrationFactory(
            project=project,
            provider=provider,
            creator=creator,
            is_public=True,
            has_doi=True
        )
        o = Outcome.objects.for_registration(r, create=True)
        o.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.ANALYTIC_CODE,
            finalized=True,
        )
        return r

    @pytest.fixture(autouse=True)
    def open_materials(self, project, provider, creator):
        r = RegistrationFactory(
            project=project,
            provider=provider,
            creator=creator,
            is_public=True,
            has_doi=True
        )
        o = Outcome.objects.for_registration(r, create=True)
        o.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.MATERIALS,
            finalized=True,
        )
        return r

    @pytest.fixture
    def open_papers(self, project, provider, creator):
        r = RegistrationFactory(
            project=project,
            provider=provider,
            creator=creator,
            is_public=True,
            has_doi=True
        )
        o = Outcome.objects.for_registration(r, create=True)
        o.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.PAPERS,
            finalized=True,
        )
        return r

    @pytest.fixture
    def open_supplements(self, project, provider, creator):
        r = RegistrationFactory(
            project=project,
            provider=provider,
            creator=creator,
            is_public=True,
            has_doi=True
        )
        o = Outcome.objects.for_registration(r, create=True)
        o.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.SUPPLEMENTS,
            finalized=True,
        )
        return r

    @pytest.fixture(params=REGISTRATION_LIST_ROUTES)
    def api_url(self, request, project, provider, creator):
        format_dict = {
            'node_id': project._id, 'user_id': creator._id, 'provider_id': provider._id
        }
        return request.param.format(**format_dict)

    def test_annotations(
        self, app, open_data, open_code, open_materials, creator, open_papers, open_supplements, api_url
    ):
        resp = app.get(api_url, auth=creator.auth, expect_errors=False)
        data = resp.json['data']

        parsed_results = {
            entry['id']: {
                'data': entry['attributes']['has_data'],
                'code': entry['attributes']['has_analytic_code'],
                'materials': entry['attributes']['has_materials'],
                'papers': entry['attributes']['has_papers'],
                'supplements': entry['attributes']['has_supplements'],
            }
            for entry in data
        }
        expected_results = {
            open_data._id: {'data': True, 'code': False, 'materials': False, 'papers': False, 'supplements': False},
            open_code._id: {'data': False, 'code': True, 'materials': False, 'papers': False, 'supplements': False},
            open_materials._id: {'data': False, 'code': False, 'materials': True, 'papers': False, 'supplements': False},
            open_papers._id: {'data': False, 'code': False, 'materials': False, 'papers': True, 'supplements': False},
            open_supplements._id: {'data': False, 'code': False, 'materials': False, 'papers': False, 'supplements': True},
        }

        assert parsed_results == expected_results

    def test_filtering__has_data(
        self, app, open_data, open_code, open_materials, creator, open_papers, open_supplements, api_url
    ):
        if api_url.startswith(f'/{API_BASE}nodes/'):
            pytest.xfail(reason='Filtering not implemented for NodeRegistratonsList')
        filter_url = f'{api_url}?filter[has_data]=True'
        resp = app.get(filter_url, auth=creator.auth, expect_errors=False)
        data = resp.json['data']

        response_ids = {entry['id'] for entry in data}
        assert response_ids == {open_data._id}

    def test_filtering__has_code(
        self, app, open_data, open_code, open_materials, creator, open_papers, open_supplements, api_url
    ):
        if api_url.startswith(f'/{API_BASE}nodes/'):
            pytest.xfail(reason='Filtering not implemented for NodeRegistratonsList')
        filter_url = f'{api_url}?filter[has_analytic_code]=True'
        resp = app.get(filter_url, auth=creator.auth, expect_errors=False)
        data = resp.json['data']

        response_ids = {entry['id'] for entry in data}
        assert response_ids == {open_code._id}

    def test_filtering__has_materials(
        self, app, open_data, open_code, open_materials, creator, open_papers, open_supplements, api_url
    ):
        if api_url.startswith(f'/{API_BASE}nodes/'):
            pytest.xfail(reason='Filtering not implemented for NodeRegistratonsList')
        filter_url = f'{api_url}?filter[has_materials]=True'
        resp = app.get(filter_url, auth=creator.auth, expect_errors=False)
        data = resp.json['data']

        response_ids = {entry['id'] for entry in data}
        assert response_ids == {open_materials._id}

    def test_filtering__has_papers(
        self, app, open_data, open_code, open_materials, creator, open_papers, open_supplements, api_url
    ):
        if api_url.startswith(f'/{API_BASE}nodes/'):
            pytest.xfail(reason='Filtering not implemented for NodeRegistratonsList')
        filter_url = f'{api_url}?filter[has_papers]=True'
        resp = app.get(filter_url, auth=creator.auth, expect_errors=False)
        data = resp.json['data']

        response_ids = {entry['id'] for entry in data}
        assert response_ids == {open_papers._id}

    def test_filtering__has_supplements(
        self, app, open_data, open_code, open_materials, creator, open_papers, open_supplements, api_url
    ):
        if api_url.startswith(f'/{API_BASE}nodes/'):
            pytest.xfail(reason='Filtering not implemented for NodeRegistratonsList')
        filter_url = f'{api_url}?filter[has_supplements]=True'
        resp = app.get(filter_url, auth=creator.auth, expect_errors=False)
        data = resp.json['data']

        response_ids = {entry['id'] for entry in data}
        assert response_ids == {open_supplements._id}
