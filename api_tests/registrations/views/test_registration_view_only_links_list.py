import pytest

from osf.utils import permissions
from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_node_view_only_links_list import (
    TestViewOnlyLinksList,
    TestViewOnlyLinksCreate,
)
from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    PrivateLinkFactory
)


@pytest.fixture()
def base_url(public_project):
    return '/{}registrations/{}/view_only_links/'.format(
        API_BASE, public_project._id)


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def read_contrib():
    return AuthUserFactory()


@pytest.fixture()
def write_contrib():
    return AuthUserFactory()


@pytest.fixture()
def non_contrib():
    return AuthUserFactory()


@pytest.fixture()
def public_project(user, read_contrib, write_contrib):
    public_project = RegistrationFactory(is_public=True, creator=user)
    public_project.add_contributor(
        read_contrib, permissions=permissions.READ)
    public_project.add_contributor(
        write_contrib, permissions=permissions.WRITE)
    public_project.save()
    return public_project


@pytest.fixture()
def view_only_link(public_project):
    view_only_link = PrivateLinkFactory(name='testlink')
    view_only_link.nodes.add(public_project)
    view_only_link.save()
    return view_only_link


class TestRegistrationViewOnlyLinksList(TestViewOnlyLinksList):
    pass


class TestRegistrationViewOnlyLinksCreate(TestViewOnlyLinksCreate):
    pass
