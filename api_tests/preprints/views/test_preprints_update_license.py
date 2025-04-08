import pytest

from rest_framework import exceptions

from osf.utils.permissions import READ
from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import (
    NodeLicense,
)
from osf.utils.permissions import WRITE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    ProjectFactory,
    PreprintProviderFactory,
)


@pytest.mark.django_db
class TestPreprintUpdateLicense:

    @pytest.fixture()
    def admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def cc0_license(self):
        return NodeLicense.objects.filter(name='CC0 1.0 Universal').first()

    @pytest.fixture()
    def mit_license(self):
        return NodeLicense.objects.filter(name='MIT License').first()

    @pytest.fixture()
    def no_license(self):
        return NodeLicense.objects.filter(name='No license').first()

    @pytest.fixture()
    def preprint_provider(self, cc0_license, no_license):
        provider = PreprintProviderFactory()
        provider.licenses_acceptable.add(*[cc0_license, no_license])
        provider.save()
        return provider

    @pytest.fixture()
    def preprint(self, admin_contrib, write_contrib, read_contrib, preprint_provider):
        test_preprint = PreprintFactory(
            creator=admin_contrib,
            provider=preprint_provider
        )
        test_preprint.add_contributor(
            write_contrib,
            permissions=WRITE,
            auth=Auth(admin_contrib)
        )
        test_preprint.add_contributor(
            read_contrib,
            auth=Auth(admin_contrib),
            permissions=READ
        )
        test_preprint.save()
        return test_preprint

    @pytest.fixture()
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/'

    def make_payload(
            self,
            node_id,
            license_id=None,
            license_year=None,
            copyright_holders=None,
            jsonapi_type='preprints'
    ):
        attributes = {}

        if license_year and copyright_holders:
            attributes = {
                'license_record': {
                    'year': license_year,
                    'copyright_holders': copyright_holders
                }
            }
        elif license_year:
            attributes = {
                'license_record': {
                    'year': license_year
                }
            }
        elif copyright_holders:
            attributes = {
                'license_record': {
                    'copyright_holders': copyright_holders
                }
            }

        return {
            'data': {
                'id': node_id,
                'type': jsonapi_type,
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
                'id': node_id,
                'type': jsonapi_type,
                'attributes': attributes
            }
        }

    def test_admin_update_license_with_invalid_id(self, app, admin_contrib, preprint, url):
        data = self.make_payload(
            node_id=preprint._id,
            license_id='thisisafakelicenseid'
        )

        assert preprint.license is None

        res = app.patch_json_api(
            url,
            data,
            auth=admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Unable to find specified license.'

        preprint.reload()
        assert preprint.license is None

    def test_admin_can_update_license(
            self,
            app,
            admin_contrib,
            preprint,
            cc0_license,
            url,
    ):
        data = self.make_payload(
            node_id=preprint._id,
            license_id=cc0_license._id
        )

        assert preprint.license is None

        res = app.patch_json_api(url, data, auth=admin_contrib.auth)
        assert res.status_code == 200
        preprint.reload()

        res_data = res.json['data']
        pp_license_id = preprint.license.node_license._id
        assert res_data['relationships']['license']['data'].get('id', None) == pp_license_id
        assert res_data['relationships']['license']['data'].get('type', None) == 'licenses'

        assert preprint.license.node_license == cc0_license
        assert preprint.license.year is None
        assert preprint.license.copyright_holders == []

        # check logs
        log = preprint.logs.latest()
        assert log.action == 'license_changed'
        assert log.params.get('preprint') == preprint._id

    def test_admin_can_update_license_record(
            self,
            app,
            admin_contrib,
            preprint,
            no_license,
            url,
    ):
        data = self.make_payload(
            node_id=preprint._id,
            license_id=no_license._id,
            license_year='2015',
            copyright_holders=['Tonya Shepoly, Lucas Pucas']
        )

        assert preprint.license is None

        res = app.patch_json_api(url, data, auth=admin_contrib.auth)
        assert res.status_code == 200
        preprint.reload()

        assert preprint.license.node_license == no_license
        assert preprint.license.year == '2015'
        assert preprint.license.copyright_holders == ['Tonya Shepoly, Lucas Pucas']

    def test_write_contrib_can_update_license(
            self,
            app,
            write_contrib,
            preprint,
            cc0_license,
            url
    ):
        data = self.make_payload(
            node_id=preprint._id,
            license_id=cc0_license._id
        )

        res = app.patch_json_api(
            url,
            data,
            auth=write_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 200
        preprint.reload()

        assert preprint.license.node_license == cc0_license

    def test_read_contrib_cannot_update_license(
            self,
            app,
            read_contrib,
            preprint,
            cc0_license,
            url
    ):
        data = self.make_payload(
            node_id=preprint._id,
            license_id=cc0_license._id
        )

        res = app.patch_json_api(
            url,
            data,
            auth=read_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_non_contrib_cannot_update_license(
            self,
            preprint,
            cc0_license,
            url,
            non_contrib,
            app
    ):
        data = self.make_payload(
            node_id=preprint._id,
            license_id=cc0_license._id
        )

        res = app.patch_json_api(
            url,
            data,
            auth=non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_unauthenticated_user_cannot_update_license
        data = self.make_payload(
            node_id=preprint._id,
            license_id=cc0_license._id
        )

        res = app.patch_json_api(url, data, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_update_preprint_with_invalid_license_for_provider(
            self,
            app,
            admin_contrib,
            preprint,
            preprint_provider,
            mit_license,
            no_license,
            url,
    ):

        #   test_update_preprint_with_invalid_license_for_provider
        data = self.make_payload(
            node_id=preprint._id,
            license_id=mit_license._id
        )

        assert preprint.license is None

        res = app.patch_json_api(
            url, data,
            auth=admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'Invalid license chosen for {}'.format(
            preprint_provider.name)

    def test_update_preprint_license_without_required_year_in_payload(
            self,
            app,
            admin_contrib,
            preprint,
            preprint_provider,
            mit_license,
            no_license,
            url,
    ):
        data = self.make_payload(
            node_id=preprint._id,
            license_id=no_license._id,
            copyright_holders=['Rachel', 'Rheisen']
        )

        res = app.patch_json_api(
            url, data,
            auth=admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'year must be specified for this license'

    def test_update_preprint_license_without_required_copyright_holders_in_payload(
            self,
            app,
            admin_contrib,
            preprint,
            preprint_provider,
            mit_license,
            no_license,
            url,
    ):
        data = self.make_payload(
            node_id=preprint._id,
            license_id=no_license._id,
            license_year='1994'
        )

        res = app.patch_json_api(
            url, data,
            auth=admin_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'copyrightHolders must be specified for this license'

    def test_update_preprint_with_existing_license_year_attribute_only(
            self,
            app,
            admin_contrib,
            preprint,
            no_license,
            url,
    ):
        preprint.set_preprint_license(
            {
                'id': no_license.license_id,
                'year': '2014',
                'copyrightHolders': ['Daniel FromBrazil', 'Queen Jaedyn']
            },
            Auth(admin_contrib),
        )
        preprint.save()

        assert preprint.license.node_license == no_license
        assert preprint.license.year == '2014'
        assert preprint.license.copyright_holders == ['Daniel FromBrazil', 'Queen Jaedyn']

        data = self.make_payload(
            node_id=preprint._id,
            license_year='2015'
        )

        res = app.patch_json_api(url, data, auth=admin_contrib.auth)
        assert res.status_code == 200
        preprint.license.reload()

        assert preprint.license.node_license == no_license
        assert preprint.license.year == '2015'
        assert preprint.license.copyright_holders == ['Daniel FromBrazil', 'Queen Jaedyn']

    def test_update_preprint_with_existing_license_copyright_holders_attribute_only(
            self,
            app,
            admin_contrib,
            preprint,
            no_license,
            url
    ):
        preprint.set_preprint_license(
            {
                'id': no_license.license_id,
                'year': '2014',
                'copyrightHolders': ['Captain Haley', 'Keegor Cannoli']
            },
            Auth(admin_contrib),
        )
        preprint.save()

        assert preprint.license.node_license == no_license
        assert preprint.license.year == '2014'
        assert preprint.license.copyright_holders == [
            'Captain Haley', 'Keegor Cannoli']

        data = self.make_payload(
            node_id=preprint._id,
            copyright_holders=['Reason Danish', 'Ben the NJB']
        )

        res = app.patch_json_api(url, data, auth=admin_contrib.auth)
        assert res.status_code == 200
        preprint.license.reload()

        assert preprint.license.node_license == no_license
        assert preprint.license.year == '2014'
        assert preprint.license.copyright_holders == ['Reason Danish', 'Ben the NJB']

    def test_update_preprint_with_existing_license_relationship_only(
            self,
            app,
            admin_contrib,
            preprint,
            cc0_license,
            no_license,
            url,
    ):
        preprint.set_preprint_license(
            {
                'id': no_license.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. Lulu']
            },
            Auth(admin_contrib),
        )
        preprint.save()

        assert preprint.license.node_license == no_license
        assert preprint.license.year == '2014'
        assert preprint.license.copyright_holders == ['Reason', 'Mr. Lulu']

        data = self.make_payload(
            node_id=preprint._id,
            license_id=cc0_license._id
        )

        res = app.patch_json_api(url, data, auth=admin_contrib.auth)
        assert res.status_code == 200
        preprint.license.reload()

        assert preprint.license.node_license == cc0_license
        assert preprint.license.year == '2014'
        assert preprint.license.copyright_holders == ['Reason', 'Mr. Lulu']

    def test_update_preprint_with_existing_license_relationship_and_attributes(
            self,
            app,
            admin_contrib,
            preprint,
            cc0_license,
            no_license,
            url,
    ):
        preprint.set_preprint_license(
            {
                'id': no_license.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. Cosgrove']
            },
            Auth(admin_contrib),
            save=True
        )

        assert preprint.license.node_license == no_license
        assert preprint.license.year == '2014'
        assert preprint.license.copyright_holders == ['Reason', 'Mr. Cosgrove']

        data = self.make_payload(
            node_id=preprint._id,
            license_id=cc0_license._id,
            license_year='2015',
            copyright_holders=['Rheisen', 'Princess Tyler']
        )

        res = app.patch_json_api(url, data, auth=admin_contrib.auth)
        assert res.status_code == 200
        preprint.license.reload()

        assert preprint.license.node_license == cc0_license
        assert preprint.license.year == '2015'
        assert preprint.license.copyright_holders == ['Rheisen', 'Princess Tyler']

    def test_update_preprint_license_does_not_change_project_license(
            self,
            app,
            admin_contrib,
            preprint,
            cc0_license,
            no_license,
            url,
    ):
        project = ProjectFactory(creator=admin_contrib)
        preprint.node = project
        preprint.save()
        preprint.node.set_node_license(
            {
                'id': no_license.license_id,
                'year': '2015',
                'copyrightHolders': ['Simba', 'Mufasa']
            },
            auth=Auth(admin_contrib)
        )
        preprint.node.save()
        assert preprint.node.node_license.node_license == no_license

        data = self.make_payload(
            node_id=preprint._id,
            license_id=cc0_license._id
        )

        res = app.patch_json_api(url, data, auth=admin_contrib.auth)
        assert res.status_code == 200
        preprint.reload()

        assert preprint.license.node_license == cc0_license
        assert preprint.node.node_license.node_license == no_license

    def test_update_preprint_license_without_change_does_not_add_log(
            self,
            app,
            admin_contrib,
            preprint,
            no_license,
            url
    ):
        preprint.set_preprint_license(
            {
                'id': no_license.license_id,
                'year': '2015',
                'copyrightHolders': ['Kim', 'Kanye']
            },
            auth=Auth(admin_contrib),
            save=True
        )

        before_num_logs = preprint.logs.count()
        before_update_log = preprint.logs.latest()

        data = self.make_payload(
            node_id=preprint._id,
            license_id=no_license._id,
            license_year='2015',
            copyright_holders=['Kanye', 'Kim']
        )
        res = app.patch_json_api(url, data, auth=admin_contrib.auth)
        preprint.reload()

        after_num_logs = preprint.logs.count()
        after_update_log = preprint.logs.latest()

        assert res.status_code == 200
        assert before_num_logs == after_num_logs
        assert before_update_log._id == after_update_log._id
