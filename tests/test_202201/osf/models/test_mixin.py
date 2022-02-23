import pytest
from nose.tools import assert_not_in

from framework.auth import Auth
from osf.models import Contributor
from osf_tests.factories import UserFactory,\
    NodeFactory, AuthUserFactory, ProjectFactory

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def node(user):
    return NodeFactory(creator=user)


@pytest.fixture()
def auth(user):
    return Auth(user)


class TestContributorMethods:

    def test_cancel_invite(self, node, auth):
        user = UserFactory()
        node.add_contributor(contributor=user, auth=auth, save=True)
        assert user in node.contributors
        node.cancel_invite(contributor=user)
        node.reload()

        assert user not in node.contributors
        assert node.logs.latest().params['contributors'] == [user._id]

    def test_cancel_invite_isinstance(self, node, auth):
        user = AuthUserFactory()
        contributor = Contributor()
        setattr(contributor, 'user', user)
        node.add_contributor(contributor=user, auth=auth, save=True)
        assert user in node.contributors

        node.cancel_invite(contributor=contributor)
        node.reload()

        assert user not in node.contributors
        assert node.logs.latest().params['contributors'] == [user._id]

    def test_cancel_invite_unclaimed_records(self, node, auth):
        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = 'given'
        given_email = 'abc@gmail.com'
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        project.save()
        project.cancel_invite(user)

        assert isinstance(user, Contributor) is False

        assert_not_in(
            project._primary_key,
            user.unclaimed_records.keys()
        )

    def test_cancel_invite_get_identifier_value(self, node, auth):
        user = AuthUserFactory()
        node.add_contributor(contributor=user, auth=auth, save=True)

        def my_function(name=''):
            return {'name': name}

        setattr(node, 'get_identifier_value', my_function)
        assert user in node.contributors

        node.cancel_invite(contributor=user)
        node.reload()

        assert user not in node.contributors
        assert node.logs.latest().params['contributors'] == [user._id]
