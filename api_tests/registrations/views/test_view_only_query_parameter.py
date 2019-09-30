import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_view_only_query_parameter import (
    TestNodeDetailViewOnlyLinks,
    TestNodeListViewOnlyLinks,
)
from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    PrivateLinkFactory,
)
from osf.models import RegistrationSchema
from osf.utils import permissions


@pytest.fixture()
def admin():
    return AuthUserFactory()


@pytest.fixture()
def base_url():
    return '/{}registrations/'.format(API_BASE)


@pytest.fixture()
def read_contrib():
    return AuthUserFactory()


@pytest.fixture()
def write_contrib():
    return AuthUserFactory()


@pytest.fixture()
def valid_contributors(admin, read_contrib, write_contrib):
    return [
        admin._id,
        read_contrib._id,
        write_contrib._id,
    ]


@pytest.fixture()
def private_node_one(admin, read_contrib, write_contrib):
    private_node_one = RegistrationFactory(
        is_public=False,
        creator=admin,
        title='Private One')
    private_node_one.add_contributor(
        read_contrib, permissions=permissions.READ, save=True)
    private_node_one.add_contributor(
        write_contrib,
        permissions=permissions.WRITE,
        save=True)
    return private_node_one


@pytest.fixture()
def private_node_one_anonymous_link(private_node_one):
    private_node_one_anonymous_link = PrivateLinkFactory(anonymous=True)
    private_node_one_anonymous_link.nodes.add(private_node_one)
    private_node_one_anonymous_link.save()
    return private_node_one_anonymous_link


@pytest.fixture()
def private_node_one_private_link(private_node_one):
    private_node_one_private_link = PrivateLinkFactory(anonymous=False)
    private_node_one_private_link.nodes.add(private_node_one)
    private_node_one_private_link.save()
    return private_node_one_private_link


@pytest.fixture()
def private_node_one_url(private_node_one):
    return '/{}registrations/{}/'.format(API_BASE, private_node_one._id)


@pytest.fixture()
def private_node_two(admin, read_contrib, write_contrib):
    private_node_two = RegistrationFactory(
        is_public=False,
        creator=admin,
        title='Private Two')
    private_node_two.add_contributor(
        read_contrib, permissions=permissions.READ, save=True)
    private_node_two.add_contributor(
        write_contrib,
        permissions=permissions.WRITE,
        save=True)
    return private_node_two


@pytest.fixture()
def private_node_two_url(private_node_two):
    return '/{}registrations/{}/'.format(API_BASE, private_node_two._id)


@pytest.fixture()
def public_node_one(admin, read_contrib, write_contrib):
    public_node_one = RegistrationFactory(
        is_public=True, creator=admin, title='Public One')
    public_node_one.add_contributor(
        read_contrib, permissions=permissions.READ, save=True)
    public_node_one.add_contributor(
        write_contrib,
        permissions=permissions.WRITE,
        save=True)
    return public_node_one


@pytest.fixture()
def public_node_one_anonymous_link(public_node_one):
    public_node_one_anonymous_link = PrivateLinkFactory(anonymous=True)
    public_node_one_anonymous_link.nodes.add(public_node_one)
    public_node_one_anonymous_link.save()
    return public_node_one_anonymous_link


@pytest.fixture()
def public_node_one_private_link(public_node_one):
    public_node_one_private_link = PrivateLinkFactory(anonymous=False)
    public_node_one_private_link.nodes.add(public_node_one)
    public_node_one_private_link.save()
    return public_node_one_private_link


@pytest.fixture()
def public_node_one_url(public_node_one):
    return '/{}registrations/{}/'.format(API_BASE, public_node_one._id)


@pytest.fixture()
def public_node_two(admin, read_contrib, write_contrib):
    public_node_two = RegistrationFactory(
        is_public=True, creator=admin, title='Public Two')
    public_node_two.add_contributor(
        read_contrib, permissions=permissions.READ, save=True)
    public_node_two.add_contributor(
        write_contrib,
        permissions=permissions.WRITE,
        save=True)
    return public_node_two


@pytest.fixture()
def public_node_two_url(public_node_two):
    return '/{}registrations/{}/'.format(API_BASE, public_node_two._id)


class TestRegistrationDetailViewOnlyLinks(TestNodeDetailViewOnlyLinks):
    @pytest.fixture()
    def registration_schema(self):
        name = 'Registered Report Protocol Preregistration'
        return RegistrationSchema.objects.get(name=name, schema_version=2)

    @pytest.fixture()
    def reg_report(self, registration_schema, admin):
        registration = RegistrationFactory(schema=registration_schema, creator=admin, is_public=False)
        registration.registered_meta[registration_schema._id] = {
            'q1': {
                'comments': [],
                'extra': [],
                'value': 'This is the answer to a question'
            },
            'q2': {
                'comments': [],
                'extra': [],
                'value': 'Grapes McGee'
            }

        }
        registration.registration_responses = registration.flatten_registration_metadata()
        registration.save()
        return registration

    @pytest.fixture()
    def reg_report_anonymous_link(self, reg_report):
        anon_link = PrivateLinkFactory(anonymous=True)
        anon_link.nodes.add(reg_report)
        anon_link.save()
        return anon_link

    def test_author_questions_are_anonymous(self, app, base_url, reg_report, admin, reg_report_anonymous_link):
        # Admin contributor sees q2 (author question)
        url = '/{}registrations/{}/'.format(API_BASE, reg_report._id)
        res = app.get(url, auth=admin.auth)
        assert res.status_code == 200
        meta = res.json['data']['attributes']['registered_meta']
        assert 'q1' in meta
        assert 'q2' in meta

        reg_responses = res.json['data']['attributes']['registration_responses']
        assert 'q1' in reg_responses
        assert 'q2' in reg_responses

        # Anonymous view only link has q2 (author response) removed
        res = app.get(url, {
            'view_only': reg_report_anonymous_link.key
        })
        assert res.status_code == 200
        meta = res.json['data']['attributes']['registered_meta']
        assert 'q1' in meta
        assert 'q2' not in meta

        reg_responses = res.json['data']['attributes']['registration_responses']
        assert 'q1' in reg_responses
        assert 'q2' not in reg_responses


class TestRegistrationListViewOnlyLinks(TestNodeListViewOnlyLinks):
    pass
