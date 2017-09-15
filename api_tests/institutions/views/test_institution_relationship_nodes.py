import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    WithdrawnRegistrationFactory,
    RegistrationFactory,
    InstitutionFactory,
    AuthUserFactory,
    NodeFactory,
)
from website.util import permissions

def make_payload(*node_ids):
    data = [
        {'type': 'nodes', 'id': id_} for id_ in node_ids
    ]
    return {'data': data}

def make_registration_payload(*node_ids):
    data = [
        {'type': 'registrations', 'id': id_} for id_ in node_ids
    ]
    return {'data': data}

@pytest.mark.django_db
class TestInstitutionRelationshipNodes:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def user(self, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        user.save()
        return user

    @pytest.fixture()
    def node_one(self, user, institution):
        node = NodeFactory(creator=user)
        node.affiliated_institutions.add(institution)
        node.save()
        return node

    @pytest.fixture()
    def node_two(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_public(self, user, institution):
        node_public = NodeFactory(is_public=True)
        node_public.affiliated_institutions.add(institution)
        node_public.save()
        return node_public

    @pytest.fixture()
    def node_private(self, user, institution):
        node_private = NodeFactory()
        node_private.affiliated_institutions.add(institution)
        node_private.save()
        return node_private

    @pytest.fixture()
    def url_institution_nodes(self, institution):
        return '/{}institutions/{}/relationships/nodes/'.format(API_BASE, institution._id)


    def test_auth_get_nodes(self, app, user, node_one, node_public, node_private, url_institution_nodes):
        #test_get_nodes_no_auth
        res = app.get(url_institution_nodes)

        assert res.status_code == 200
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node_one._id not in node_ids
        assert node_public._id in node_ids
        assert node_private._id not in node_ids

        #test_get_nodes_with_auth
        res = app.get(url_institution_nodes, auth=user.auth)

        assert res.status_code == 200
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node_one._id in node_ids
        assert node_public._id in node_ids
        assert node_private._id not in node_ids

    def test_node_or_type_does_not_exist(self, app, user, node_two, url_institution_nodes):
        #test_node_does_not_exist
        res = app.post_json_api(
            url_institution_nodes,
            make_payload('notIdatAll'),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 404

        #test_node_type_does_not_exist
        res = app.post_json_api(
            url_institution_nodes,
            {'data': [{'type': 'dugtrio', 'id': node_two._id}]},
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 409

    def test_user_with_nodes_and_permissions(self, user, app, node_two, url_institution_nodes, institution):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_two._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node_two._id in node_ids

        node_two.reload()
        assert institution in node_two.affiliated_institutions.all()

    def test_user_does_not_have_node(self, app, node, url_institution_nodes, user, institution):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_user_is_admin(self, app, node_two, url_institution_nodes, user, institution):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_two._id),
            auth=user.auth
        )
        assert res.status_code == 201
        node_two.reload()
        assert institution in node_two.affiliated_institutions.all()

    def test_user_is_read_write(self, app, node, url_institution_nodes, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        node.add_contributor(user)
        node.save()
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node.reload()
        assert institution in node.affiliated_institutions.all()

    def test_user_is_read_only(self, app, node, url_institution_nodes, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        node.add_contributor(user, permissions=[permissions.READ])
        node.save()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_user_is_admin_but_not_affiliated(self, app, url_institution_nodes, institution):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_add_some_with_permissions_others_without(self, user, node, node_two, app, url_institution_nodes, institution):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_two._id, node._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
        node_two.reload()
        node.reload()
        assert institution not in node_two.affiliated_institutions.all()
        assert institution not in node.affiliated_institutions.all()

    def test_add_some_existant_others_not(self, institution, node_one, node_two, app, url_institution_nodes, user):
        assert institution in node_one.affiliated_institutions.all()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_two._id, node_one._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node_one.reload()
        node_two.reload()
        assert institution in node_one.affiliated_institutions.all()
        assert institution in node_two.affiliated_institutions.all()

    def test_only_add_existent_with_mixed_permissions(self, institution, node_one, node_public, app, url_institution_nodes, user):
        assert institution in node_one.affiliated_institutions.all()
        assert institution in node_public.affiliated_institutions.all()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_public._id, node_one._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
        node_one.reload()
        node_public.reload()
        assert institution in node_one.affiliated_institutions.all()
        assert institution in node_public.affiliated_institutions.all()

    def test_only_add_existent_with_permissions(self, user, node_one, node_two, institution, app, url_institution_nodes):
        node_two.affiliated_institutions.add(institution)
        node_two.save()
        assert institution in node_one.affiliated_institutions.all()
        assert institution in node_two.affiliated_institutions.all()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_two._id, node_one._id),
            auth=user.auth
        )

        assert res.status_code == 204

    def test_delete_user_is_admin(self, app, url_institution_nodes, node_one, user, institution):
        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_one._id),
            auth=user.auth
        )
        node_one.reload()
        assert res.status_code == 204
        assert institution not in node_one.affiliated_institutions.all()

    def test_delete_user_is_read_write(self, app, node_private, user, url_institution_nodes, institution):
        node_private.add_contributor(user)
        node_private.save()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_private._id),
            auth=user.auth
        )
        node_private.reload()

        assert res.status_code == 204
        assert institution not in node_private.affiliated_institutions.all()

    def test_delete_user_is_read_only(self, node_private, user, app, url_institution_nodes, institution):
        node_private.add_contributor(user, permissions='read')
        node_private.save()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_private._id),
            auth=user.auth,
            expect_errors=True
        )
        node_private.reload()

        assert res.status_code == 403
        assert institution in node_private.affiliated_institutions.all()

    def test_delete_user_is_admin_and_affiliated_with_inst(self, institution, node_one, app, url_institution_nodes, user):
        assert institution in node_one.affiliated_institutions.all()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_one._id),
            auth=user.auth
        )

        assert res.status_code == 204
        node_one.reload()
        assert institution not in node_one.affiliated_institutions.all()

    def test_delete_user_is_admin_but_not_affiliated_with_inst(self, institution, app, url_institution_nodes):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        node.affiliated_institutions.add(institution)
        node.save()
        assert institution in node.affiliated_institutions.all()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth
        )

        assert res.status_code == 204
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_delete_user_is_affiliated_with_inst_and_mixed_permissions_on_nodes(self, app, url_institution_nodes, node_one, node_public, user):
        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_one._id, node_public._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403

    def test_add_non_node(self, app, user, institution, url_institution_nodes):
        registration = RegistrationFactory(creator=user, is_public=True)
        registration.affiliated_institutions.add(institution)
        registration.save()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(registration._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 404


@pytest.mark.django_db
class TestInstitutionRelationshipRegistrations:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def admin(self, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        user.save()
        return user

    @pytest.fixture()
    def user(self, institution):
        return AuthUserFactory()

    @pytest.fixture()
    def affiliated_user(self, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        user.save()
        return user

    @pytest.fixture()
    def registration_no_owner(self):
        return RegistrationFactory(is_public=True)

    @pytest.fixture()
    def registration_no_affiliation(self, admin):
        return RegistrationFactory(creator=admin)

    @pytest.fixture()
    def registration_pending(self, admin, institution):
        registration = RegistrationFactory(creator=admin)
        registration.affiliated_institutions.add(institution)
        registration.save()
        return registration

    @pytest.fixture()
    def registration_public(self, admin, institution):
        registration = RegistrationFactory(creator=admin, is_public=True)
        registration.affiliated_institutions.add(institution)
        registration.save()
        return registration

    @pytest.fixture()
    def url_institution_registrations(self, institution):
        return '/{}institutions/{}/relationships/registrations/'.format(API_BASE, institution._id)


    def test_auth_get_registrations(self, app, admin, registration_no_owner, registration_no_affiliation, registration_pending, registration_public, url_institution_registrations):

        #test getting registrations without auth (for complete registrations)
        res = app.get(url_institution_registrations)
        assert res.status_code == 200
        registration_ids = [reg['id'] for reg in res.json['data']]
        assert registration_no_affiliation._id not in registration_ids
        assert registration_pending._id not in registration_ids
        assert registration_no_owner._id not in registration_ids
        assert registration_public._id in registration_ids

        #Withdraw a registration, make sure it still shows up
        WithdrawnRegistrationFactory(registration=registration_public, user=admin)

        #test getting registrations with auth (for embargoed and pending)
        res = app.get(url_institution_registrations, auth=admin.auth)
        assert res.status_code == 200
        registration_ids = [reg['id'] for reg in res.json['data']]
        assert registration_no_affiliation._id not in registration_ids
        assert registration_pending._id in registration_ids
        assert registration_public._id in registration_ids
        assert registration_no_owner._id not in registration_ids

    def test_add_incorrect_permissions(self, app, admin, user, affiliated_user, registration_no_affiliation, url_institution_registrations, institution):
        # No authentication
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            expect_errors=True,
        )
        assert res.status_code == 401

        # User has no permission
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            expect_errors=True,
            auth = AuthUserFactory().auth
        )
        assert res.status_code == 403

        # User has read permission
        registration_no_affiliation.add_contributor(affiliated_user, permissions=[permissions.READ])
        registration_no_affiliation.save()

        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # User is admin but not affiliated
        registration = RegistrationFactory(creator=user)
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration._id),
            expect_errors=True,
            auth=user.auth
        )
        assert res.status_code == 403
        registration.reload()
        assert institution not in registration.affiliated_institutions.all()

        # Registration does not exist
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload('notIdatAll'),
            expect_errors=True,
            auth=admin.auth
        )
        assert res.status_code == 404

        # Attempt to use endpoint on Node
        res = app.post_json_api(
            url_institution_registrations,
            {'data': [{'type': 'nodes', 'id': NodeFactory(creator=admin)._id}]},
            expect_errors=True,
            auth=admin.auth
        )
        assert res.status_code == 409

        registration_no_affiliation.reload()
        assert institution not in registration_no_affiliation.affiliated_institutions.all()

    def test_add_some_with_permissions_others_without(self, admin, registration_no_affiliation, registration_no_owner, app, url_institution_registrations, institution):
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_owner._id, registration_no_affiliation._id),
            expect_errors=True,
            auth=admin.auth
        )

        assert res.status_code == 403
        registration_no_owner.reload()
        registration_no_affiliation.reload()
        assert institution not in registration_no_owner.affiliated_institutions.all()
        assert institution not in registration_no_affiliation.affiliated_institutions.all()

    def test_add_user_is_admin(self, admin, app, registration_no_affiliation, url_institution_registrations, institution):
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            auth=admin.auth
        )

        assert res.status_code == 201
        registration_no_affiliation.reload()
        assert institution in registration_no_affiliation.affiliated_institutions.all()

    def test_add_withdrawn_registration(self, app, url_institution_registrations, admin, registration_no_affiliation, institution):
        WithdrawnRegistrationFactory(registration=registration_no_affiliation, user=admin)

        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            auth=admin.auth
        )

        assert res.status_code == 201
        registration_no_affiliation.reload()
        assert institution in registration_no_affiliation.affiliated_institutions.all()

    def test_add_user_is_read_write(self, app, affiliated_user, registration_no_affiliation, url_institution_registrations, institution):
        registration_no_affiliation.add_contributor(affiliated_user)
        registration_no_affiliation.save()
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            auth=affiliated_user.auth
        )

        assert res.status_code == 201
        registration_no_affiliation.reload()
        assert institution in registration_no_affiliation.affiliated_institutions.all()

    def test_add_already_added(self, admin, app, registration_pending, url_institution_registrations, institution):
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_pending._id),
            auth=admin.auth
        )

        assert res.status_code == 204
        registration_pending.reload()
        assert institution in registration_pending.affiliated_institutions.all()

    def test_delete_user_is_admin(self, app, url_institution_registrations, registration_pending, admin, institution):
        res = app.delete_json_api(
            url_institution_registrations,
            make_registration_payload(registration_pending._id),
            auth=admin.auth
        )
        registration_pending.reload()
        assert res.status_code == 204
        assert institution not in registration_pending.affiliated_institutions.all()

    def test_delete_user_is_read_write(self, app, affiliated_user, registration_pending, url_institution_registrations, institution):
        registration_pending.add_contributor(affiliated_user)
        registration_pending.save()

        res = app.delete_json_api(
            url_institution_registrations,
            make_registration_payload(registration_pending._id),
            auth=affiliated_user.auth
        )
        registration_pending.reload()

        assert res.status_code == 204
        assert institution not in registration_pending.affiliated_institutions.all()

    def test_delete_user_is_admin_but_not_affiliated_with_inst(self, user, institution, app, url_institution_registrations):
        registration = RegistrationFactory(creator=user)
        registration.affiliated_institutions.add(institution)
        registration.save()
        assert institution in registration.affiliated_institutions.all()

        res = app.delete_json_api(
            url_institution_registrations,
            make_registration_payload(registration._id),
            auth=user.auth
        )

        assert res.status_code == 204
        registration.reload()
        assert institution not in registration.affiliated_institutions.all()
