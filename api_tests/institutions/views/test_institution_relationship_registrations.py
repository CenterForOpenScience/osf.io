import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    WithdrawnRegistrationFactory,
    RegistrationFactory,
    InstitutionFactory,
    AuthUserFactory,
    NodeFactory,
)
from osf.utils import permissions

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
class TestInstitutionRelationshipRegistrations:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def admin(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        user.save()
        return user

    @pytest.fixture()
    def user(self, institution):
        return AuthUserFactory()

    @pytest.fixture()
    def affiliated_user(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
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
        return '/{}institutions/{}/relationships/registrations/'.format(
            API_BASE, institution._id)

    def test_auth_get_registrations(
            self, app, admin, registration_no_owner,
            registration_no_affiliation,
            registration_pending, registration_public,
            url_institution_registrations
    ):

        # test getting registrations without auth (for complete registrations)
        res = app.get(url_institution_registrations)
        assert res.status_code == 200
        registration_ids = [reg['id'] for reg in res.json['data']]
        assert registration_no_affiliation._id not in registration_ids
        assert registration_pending._id not in registration_ids
        assert registration_no_owner._id not in registration_ids
        assert registration_public._id in registration_ids

        # Withdraw a registration, make sure it still shows up
        WithdrawnRegistrationFactory(
            registration=registration_public, user=admin)

        # test getting registrations with auth (for embargoed and pending)
        res = app.get(url_institution_registrations, auth=admin.auth)
        assert res.status_code == 200
        registration_ids = [reg['id'] for reg in res.json['data']]
        assert registration_no_affiliation._id not in registration_ids
        assert registration_pending._id in registration_ids
        assert registration_public._id in registration_ids
        assert registration_no_owner._id not in registration_ids

    def test_no_auth(self, app, admin, user, affiliated_user, registration_no_affiliation, url_institution_registrations):
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            expect_errors=True,
        )
        assert res.status_code == 401

    def test_no_permission(self, app, admin, user, affiliated_user, registration_no_affiliation,
                           url_institution_registrations):
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            expect_errors=True, auth=AuthUserFactory().auth
        )
        assert res.status_code == 403

    def test_read_permission(self, app, admin, user, affiliated_user, registration_no_affiliation,
                             url_institution_registrations):
        registration_no_affiliation.add_contributor(
            affiliated_user,
            permissions=permissions.READ,
            save=True
        )
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_admin_permission_not_affiliated(self, app, admin, user, affiliated_user, registration_no_affiliation,
                                             institution, url_institution_registrations):
        registration = RegistrationFactory(creator=user)
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration._id),
            expect_errors=True, auth=user.auth
        )
        assert res.status_code == 403
        assert institution not in registration.affiliated_institutions.all()

    def test_does_not_exist(self, app, admin, user, affiliated_user, registration_no_affiliation, institution,
                                                 url_institution_registrations):
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

        assert institution not in registration_no_affiliation.affiliated_institutions.all()

    def test_add_some_with_permissions_others_without(
            self, admin, app, registration_no_affiliation, registration_no_owner, url_institution_registrations,
            institution):
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(
                registration_no_owner._id,
                registration_no_affiliation._id
            ),
            expect_errors=True,
            auth=admin.auth
        )

        assert res.status_code == 403
        assert institution not in registration_no_owner.affiliated_institutions.all()
        assert institution not in registration_no_affiliation.affiliated_institutions.all()

    def test_add_user_is_admin(self, admin, app, registration_no_affiliation, url_institution_registrations,
                               institution):
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            auth=admin.auth
        )
        assert res.status_code == 201
        assert institution in registration_no_affiliation.affiliated_institutions.all()

    def test_add_withdrawn_registration(self, app, url_institution_registrations, admin, registration_no_affiliation,
            institution):
        WithdrawnRegistrationFactory(
            registration=registration_no_affiliation,
            user=admin
        )
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            auth=admin.auth
        )
        assert res.status_code == 201
        assert institution in registration_no_affiliation.affiliated_institutions.all()

    def test_add_user_is_read_write(self, app, affiliated_user, registration_no_affiliation,
                                    url_institution_registrations, institution):
        registration_no_affiliation.add_contributor(affiliated_user)
        registration_no_affiliation.save()
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_no_affiliation._id),
            auth=affiliated_user.auth
        )

        assert res.status_code == 201
        assert institution in registration_no_affiliation.affiliated_institutions.all()

    def test_add_already_added(self, admin, app, registration_pending, url_institution_registrations, institution):
        res = app.post_json_api(
            url_institution_registrations,
            make_registration_payload(registration_pending._id),
            auth=admin.auth
        )

        assert res.status_code == 204
        assert institution in registration_pending.affiliated_institutions.all()

    def test_delete_user_is_admin(self, app, url_institution_registrations, registration_pending, admin, institution):
        res = app.delete_json_api(
            url_institution_registrations,
            make_registration_payload(registration_pending._id),
            auth=admin.auth
        )
        assert res.status_code == 204
        assert institution not in registration_pending.affiliated_institutions.all()

    def test_delete_user_is_read_write(self, app, affiliated_user, registration_pending, url_institution_registrations,
                                       institution):
        registration_pending.add_contributor(affiliated_user)
        registration_pending.save()

        res = app.delete_json_api(
            url_institution_registrations,
            make_registration_payload(registration_pending._id),
            auth=affiliated_user.auth
        )
        assert res.status_code == 204
        assert institution not in registration_pending.affiliated_institutions.all()

    def test_delete_user_is_admin_but_not_affiliated_with_inst(self, user, institution, app,
                                                               url_institution_registrations):
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
        assert institution not in registration.affiliated_institutions.all()
