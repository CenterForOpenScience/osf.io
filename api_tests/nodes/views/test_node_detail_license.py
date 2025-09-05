import pytest
from rest_framework import exceptions

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models.licenses import NodeLicense
from osf.utils import permissions
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    AuthUserFactory,
    NodeLicenseRecordFactory,
)


@pytest.mark.django_db
class TestNodeLicense:

    @pytest.fixture()
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def license_name(self):
        return 'MIT License'

    @pytest.fixture()
    def node_license(self, license_name):
        return NodeLicense.objects.filter(name=license_name).first()

    @pytest.fixture()
    def year(self):
        return '2105'

    @pytest.fixture()
    def copyright_holders(self):
        return ['Foo', 'Bar']

    @pytest.fixture()
    def project_public(
            self, user, user_admin, node_license,
            year, copyright_holders):
        project_public = ProjectFactory(
            title='Project One', is_public=True, creator=user)
        project_public.add_contributor(
            user_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True)
        project_public.add_contributor(
            user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        project_public.node_license = NodeLicenseRecordFactory(
            node_license=node_license,
            year=year,
            copyright_holders=copyright_holders
        )
        project_public.save()
        return project_public

    @pytest.fixture()
    def project_private(
            self, user, user_admin, node_license,
            year, copyright_holders):
        project_private = ProjectFactory(
            title='Project Two', is_public=False, creator=user)
        project_private.add_contributor(
            user_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True
        )
        project_private.add_contributor(
            user,
            permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            save=True
        )
        project_private.node_license = NodeLicenseRecordFactory(
            node_license=node_license,
            year=year,
            copyright_holders=copyright_holders
        )
        project_private.save()
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return f'/{API_BASE}nodes/{project_public._id}/'

    @pytest.fixture()
    def url_private(self, project_private):
        return f'/{API_BASE}nodes/{project_private._id}/'

    def test_node_has(
            self, app, user, node_license, project_public,
            project_private, url_private, url_public):

        #   test_public_node_has_node_license
        res = app.get(url_public)
        assert project_public.node_license.year == res.json[
            'data']['attributes']['node_license']['year']

    #   test_public_node_has_license_relationship
        res = app.get(url_public)
        expected_license_url = '/{}licenses/{}'.format(
            API_BASE, node_license._id)
        actual_license_url = res.json['data']['relationships']['license']['links']['related']['href']
        assert expected_license_url in actual_license_url

    #   test_private_node_has_node_license
        res = app.get(url_private, auth=user.auth)
        assert project_private.node_license.year == res.json[
            'data']['attributes']['node_license']['year']

    #   test_private_node_has_license_relationship
        res = app.get(url_private, auth=user.auth)
        expected_license_url = '/{}licenses/{}'.format(
            API_BASE, node_license._id)
        actual_license_url = res.json['data']['relationships']['license']['links']['related']['href']
        assert expected_license_url in actual_license_url

    def test_component_return_parent_license_if_no_license(
            self, app, user, node_license, project_public):
        node = NodeFactory(parent=project_public, creator=user)
        node.save()
        node_url = f'/{API_BASE}nodes/{node._id}/'
        res = app.get(node_url, auth=user.auth)
        assert not node.node_license
        assert project_public.node_license.year == \
               res.json['data']['attributes']['node_license']['year']
        actual_license_url = res.json['data']['relationships']['license']['links']['related']['href']
        expected_license_url = '/{}licenses/{}'.format(
            API_BASE, node_license._id)
        assert expected_license_url in actual_license_url


@pytest.mark.django_db
class TestNodeUpdateLicense:

    @pytest.fixture()
    def user_admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        node = NodeFactory(creator=user_admin_contrib)
        node.add_contributor(user_write_contrib, auth=Auth(user_admin_contrib))
        node.add_contributor(
            user_read_contrib,
            auth=Auth(user_admin_contrib),
            permissions=permissions.READ)
        node.save()
        return node

    @pytest.fixture()
    def license_cc0(self):
        return NodeLicense.objects.filter(name='CC0 1.0 Universal').first()

    @pytest.fixture()
    def license_mit(self):
        return NodeLicense.objects.filter(name='MIT License').first()

    @pytest.fixture()
    def license_no(self):
        return NodeLicense.objects.get(name='No license')

    @pytest.fixture()
    def url_node(self, node):
        return f'/{API_BASE}nodes/{node._id}/'

    @pytest.fixture()
    def make_payload(self):
        def payload(
                node_id, license_id=None, license_year=None,
                copyright_holders=None):
            attributes = {}

            if license_year and copyright_holders:
                attributes = {
                    'node_license': {
                        'year': license_year,
                        'copyright_holders': copyright_holders
                    }
                }
            elif license_year:
                attributes = {
                    'node_license': {
                        'year': license_year
                    }
                }
            elif copyright_holders:
                attributes = {
                    'node_license': {
                        'copyright_holders': copyright_holders
                    }
                }

            return {
                'data': {
                    'type': 'nodes',
                    'id': node_id,
                    'attributes': attributes,
                    'relationships': {
                        'license': {
                            'data': {
                                'type': 'licenses',
                                'id': license_id
                            }
                        }
                    }
                }
            } if license_id else {
                'data': {
                    'type': 'nodes',
                    'id': node_id,
                    'attributes': attributes
                }
            }
        return payload

    @pytest.fixture()
    def make_request(self, app):
        def request(url, data, auth=None, expect_errors=False):
            return app.patch_json_api(
                url, data, auth=auth, expect_errors=expect_errors)
        return request

    def test_admin_update_license_with_invalid_id(
            self, user_admin_contrib, node, make_payload,
            make_request, url_node):
        data = make_payload(
            node_id=node._id,
            license_id='thisisafakelicenseid'
        )

        assert node.node_license is None

        res = make_request(
            url_node, data,
            auth=user_admin_contrib.auth,
            expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Unable to find specified license.'

        node.reload()
        assert node.node_license is None

    def test_admin_can_update_license(
            self, user_admin_contrib, node,
            make_payload, make_request,
            license_cc0, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        assert node.node_license is None

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.reload()

        assert node.node_license.node_license == license_cc0
        assert node.node_license.year is None
        assert node.node_license.copyright_holders == []

    def test_admin_can_update_license_record(
            self, user_admin_contrib, node,
            make_payload, make_request,
            license_no, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_no._id,
            license_year='2015',
            copyright_holders=['Mr. Monument', 'Princess OSF']
        )

        assert node.node_license is None

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.reload()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2015'
        assert node.node_license.copyright_holders == [
            'Mr. Monument', 'Princess OSF']

    def test_update(
            self, user_write_contrib, user_read_contrib,
            user_non_contrib, node, make_payload,
            make_request, license_cc0, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(
            url_node, data,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['id'] == node._id

    # def test_read_contributor_cannot_update_license(self):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(
            url_node, data,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    # def test_non_contributor_cannot_update_license(self):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(
            url_node, data,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    # def test_unauthenticated_user_cannot_update_license(self):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(url_node, data, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_update_node_with_existing_license_year_attribute_only(
            self, user_admin_contrib, node, make_payload,
            make_request, license_no, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. E']
            },
            Auth(user_admin_contrib),
        )
        node.save()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

        data = make_payload(
            node_id=node._id,
            license_year='2015'
        )

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.node_license.reload()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2015'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

    def test_update_node_with_existing_license_copyright_holders_attribute_only(
            self, user_admin_contrib, node, make_payload, make_request, license_no, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. E']
            },
            Auth(user_admin_contrib),
        )
        node.save()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

        data = make_payload(
            node_id=node._id,
            copyright_holders=['Mr. Monument', 'Princess OSF']
        )

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.node_license.reload()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == [
            'Mr. Monument', 'Princess OSF']

    def test_update_node_with_existing_license_relationship_only(
            self, user_admin_contrib, node, make_payload,
            make_request, license_cc0, license_no, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. E']
            },
            Auth(user_admin_contrib),
        )
        node.save()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.node_license.reload()

        assert node.node_license.node_license == license_cc0
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

    def test_update_node_with_existing_license_relationship_and_attributes(
            self, user_admin_contrib, node, make_payload, make_request,
            license_no, license_cc0, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. E']
            },
            Auth(user_admin_contrib),
            save=True
        )

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id,
            license_year='2015',
            copyright_holders=['Mr. Monument', 'Princess OSF']
        )

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.node_license.reload()

        assert node.node_license.node_license == license_cc0
        assert node.node_license.year == '2015'
        assert node.node_license.copyright_holders == [
            'Mr. Monument', 'Princess OSF']

    def test_update_node_license_without_required_year_in_payload(
            self, user_admin_contrib, node, make_payload,
            make_request, license_no, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_no._id,
            copyright_holders=['Rick', 'Morty']
        )

        res = make_request(
            url_node, data,
            auth=user_admin_contrib.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'year must be specified for this license'

    def test_update_node_license_without_license_id(
            self, node, make_payload, make_request, url_node, user_admin_contrib):
        data = make_payload(
            node_id=node._id,
            license_year='2015',
            copyright_holders=['Ben, Jerry']
        )

        res = make_request(
            url_node, data,
            auth=user_admin_contrib.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'License ID must be provided for a Node License.'

    def test_update_node_license_without_required_copyright_holders_in_payload_(
            self, user_admin_contrib, node, make_payload, make_request, license_no, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_no._id,
            license_year='1994'
        )

        res = make_request(
            url_node, data,
            auth=user_admin_contrib.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'copyrightHolders must be specified for this license'

    def test_update_node_license_adds_log(
            self, user_admin_contrib, node, make_payload,
            make_request, license_cc0, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )
        logs_before_update = node.logs.count()

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.reload()
        logs_after_update = node.logs.count()

        assert logs_before_update != logs_after_update
        assert node.logs.latest().action == 'license_changed'

    def test_update_node_license_without_change_does_not_add_log(
            self, user_admin_contrib, node, make_payload,
            make_request, license_no, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2015',
                'copyrightHolders': ['Kim', 'Kanye']
            },
            auth=Auth(user_admin_contrib),
            save=True
        )

        before_num_logs = node.logs.count()
        before_update_log = node.logs.latest()

        data = make_payload(
            node_id=node._id,
            license_id=license_no._id,
            license_year='2015',
            copyright_holders=['Kanye', 'Kim']
        )
        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        node.reload()

        after_num_logs = node.logs.count()
        after_update_log = node.logs.latest()

        assert res.status_code == 200
        assert before_num_logs == after_num_logs
        assert before_update_log._id == after_update_log._id
