import pytest

from osf.utils.workflows import DefaultStates, RequestTypes
from osf_tests.factories import (
    AuthUserFactory,
    NodeRequestFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PreprintRequestFactory,
    ProjectFactory,
)
from osf.utils import permissions

@pytest.mark.django_db
class NodeRequestTestMixin(object):

    @pytest.fixture()
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def requester(self):
        return AuthUserFactory()

    @pytest.fixture()
    def noncontrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, admin, write_contrib):
        proj = ProjectFactory(creator=admin)
        proj.save()
        proj.add_contributor(
            contributor=write_contrib,
            permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            send_email='access_request',
            save=True
        )
        return proj

    @pytest.fixture()
    def node_request(self, project, requester):
        node_request = NodeRequestFactory(
            creator=requester,
            target=project,
            request_type=RequestTypes.ACCESS.value,
            machine_state=DefaultStates.INITIAL.value
        )
        node_request.run_submit(requester)
        return node_request

    @pytest.fixture()
    def second_admin(self, project):
        second_admin = AuthUserFactory()
        project.add_contributor(
            contributor=second_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True
        )
        return second_admin

@pytest.mark.django_db
class PreprintRequestTestMixin(object):

    @pytest.fixture()
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def noncontrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def moderator(self):
        return AuthUserFactory()

    @pytest.fixture()
    def pre_mod_provider(self, moderator):
        ppp = PreprintProviderFactory(reviews_workflow='pre-moderation')
        ppp.get_group('moderator').user_set.add(moderator)
        return ppp

    @pytest.fixture()
    def post_mod_provider(self, moderator):
        ppp = PreprintProviderFactory(reviews_workflow='post-moderation')
        ppp.get_group('moderator').user_set.add(moderator)
        return ppp

    @pytest.fixture()
    def none_mod_provider(self):
        return PreprintProviderFactory(reviews_workflow=None)

    @pytest.fixture()
    def pre_mod_preprint(self, admin, write_contrib, pre_mod_provider):
        pre = PreprintFactory(
            creator=admin,
            provider=pre_mod_provider,
            is_published=False,
            machine_state='pending'
        )
        pre.ever_public = True
        pre.save()
        pre.add_contributor(
            contributor=write_contrib,
            permissions='write',
            save=True
        )
        pre.is_public = True
        pre.save()
        return pre

    @pytest.fixture()
    def auto_withdrawable_pre_mod_preprint(self, admin, write_contrib, pre_mod_provider):
        pre = PreprintFactory(
            creator=admin,
            provider=pre_mod_provider,
            is_published=False,
            machine_state='pending'
        )
        pre.save()
        pre.add_contributor(
            contributor=write_contrib,
            permissions='write',
            save=True
        )
        return pre

    @pytest.fixture()
    def post_mod_preprint(self, admin, write_contrib, post_mod_provider):
        post = PreprintFactory(
            creator=admin,
            provider=post_mod_provider,
        )
        post.save()
        post.add_contributor(
            contributor=write_contrib,
            permissions='write',
            save=True
        )
        return post

    @pytest.fixture()
    def none_mod_preprint(self, admin, write_contrib, none_mod_provider):
        preprint = PreprintFactory(
            creator=admin,
            provider=none_mod_provider,
        )
        preprint.save()
        preprint.add_contributor(
            contributor=write_contrib,
            permissions='write',
            save=True
        )
        return preprint

    @pytest.fixture()
    def pre_request(self, pre_mod_preprint, admin):
        request = PreprintRequestFactory(
            creator=admin,
            target=pre_mod_preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value
        )
        request.run_submit(admin)
        return request

    @pytest.fixture()
    def post_request(self, post_mod_preprint, admin):
        request = PreprintRequestFactory(
            creator=admin,
            target=post_mod_preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value
        )
        request.run_submit(admin)
        return request

    @pytest.fixture()
    def none_request(self, none_mod_preprint, admin):
        request = PreprintRequestFactory(
            creator=admin,
            target=none_mod_preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value
        )
        request.run_submit(admin)
        return request

    @pytest.fixture()
    def auto_approved_pre_request(self, auto_withdrawable_pre_mod_preprint, admin):
        request = PreprintRequestFactory(
            creator=admin,
            target=auto_withdrawable_pre_mod_preprint,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value
        )
        request.run_submit(admin)
        return request
