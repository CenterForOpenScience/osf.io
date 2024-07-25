import pytest

from osf.utils.permissions import READ, WRITE, ADMIN
from api.base.settings.defaults import API_BASE
from osf.models import PreprintLog
from osf_tests.factories import PreprintFactory, AuthUserFactory


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


@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestPreprintUpdateWithAuthorAssertion:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/'

    @pytest.fixture()
    def read_contrib(self, preprint):
        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, READ)
        return contrib

    @pytest.fixture()
    def write_contrib(self, preprint):
        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, WRITE)
        return contrib

    @pytest.fixture()
    def admin_contrib(self, preprint):
        contrib = AuthUserFactory()
        preprint.add_contributor(contrib, ADMIN)
        return contrib

    def assert_permission(self, app, url, contrib, attributes, expected_status):
        update_payload = build_preprint_update_payload(node_id=contrib._id, attributes=attributes)
        res = app.patch_json_api(url, update_payload, auth=contrib.auth, expect_errors=True)
        assert res.status_code == expected_status

    # Testing permissions for updating has_coi
    def test_update_has_coi_permission_denied(self, app, read_contrib, url):
        self.assert_permission(app, url, read_contrib, {'has_coi': True}, 403)

    def test_update_has_coi_permission_granted_write(self, app, write_contrib, url):
        self.assert_permission(app, url, write_contrib, {'has_coi': True}, 200)

    def test_update_has_coi_permission_granted_admin(self, app, admin_contrib, url):
        self.assert_permission(app, url, admin_contrib, {'has_coi': True}, 200)

    def test_update_has_coi_permission_granted_creator(self, app, user, url):
        self.assert_permission(app, url, user, {'has_coi': True}, 200)

    # Testing permissions for updating conflict_of_interest_statement
    def test_update_conflict_of_interest_statement_permission_denied(self, app, read_contrib, url):
        self.assert_permission(app, url, read_contrib, {'conflict_of_interest_statement': 'Test'}, 403)

    def test_update_conflict_of_interest_statement_permission_granted_write(self, app, write_contrib, preprint, url):
        preprint.has_coi = True
        preprint.save()
        self.assert_permission(app, url, write_contrib, {'conflict_of_interest_statement': 'Test'}, 200)

    def test_update_conflict_of_interest_statement_permission_granted_admin(self, app, admin_contrib, preprint, url):
        preprint.has_coi = True
        preprint.save()
        self.assert_permission(app, url, admin_contrib, {'conflict_of_interest_statement': 'Test'}, 200)

    def test_update_conflict_of_interest_statement_permission_granted_creator(self, app, user, preprint, url):
        preprint.has_coi = True
        preprint.save()
        self.assert_permission(app, url, user, {'conflict_of_interest_statement': 'Test'}, 200)

    # Testing permissions for updating has_data_links
    def test_update_has_data_links_permission_denied(self, app, read_contrib, url):
        self.assert_permission(app, url, read_contrib, {'has_data_links': 'available'}, 403)

    def test_update_has_data_links_permission_granted_write(self, app, write_contrib, url):
        self.assert_permission(app, url, write_contrib, {'has_data_links': 'available'}, 200)

    def test_update_has_data_links_permission_granted_admin(self, app, admin_contrib, url):
        self.assert_permission(app, url, admin_contrib, {'has_data_links': 'available'}, 200)

    def test_update_has_data_links_permission_granted_creator(self, app, user, url):
        self.assert_permission(app, url, user, {'has_data_links': 'available'}, 200)

    # Testing permissions for updating why_no_data
    def test_update_why_no_data_permission_denied(self, app, read_contrib, url):
        self.assert_permission(app, url, read_contrib, {'why_no_data': 'My dog ate it.'}, 403)

    def test_update_why_no_data_permission_granted_write(self, app, write_contrib, preprint, url):
        preprint.has_data_links = 'no'
        preprint.save()
        self.assert_permission(app, url, write_contrib, {'why_no_data': 'My dog ate it.'}, 200)

    def test_update_why_no_data_permission_granted_admin(self, app, admin_contrib, preprint, url):
        preprint.has_data_links = 'no'
        preprint.save()
        self.assert_permission(app, url, admin_contrib, {'why_no_data': 'My dog ate it.'}, 200)

    def test_update_why_no_data_permission_granted_creator(self, app, user, preprint, url):
        preprint.has_data_links = 'no'
        preprint.save()
        self.assert_permission(app, url, user, {'why_no_data': 'My dog ate it.'}, 200)

    # Testing permissions for updating data_links
    def test_update_data_links_permission_denied(self, app, read_contrib, url):
        data_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        self.assert_permission(app, url, read_contrib, {'data_links': data_links}, 403)

    def test_update_data_links_permission_granted_write(self, app, write_contrib, preprint, url):
        data_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        preprint.has_data_links = 'available'
        preprint.save()
        self.assert_permission(app, url, write_contrib, {'data_links': data_links}, 200)

    def test_update_data_links_permission_granted_admin(self, app, admin_contrib, preprint, url):
        data_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        preprint.has_data_links = 'available'
        preprint.save()
        self.assert_permission(app, url, admin_contrib, {'data_links': data_links}, 200)

    def test_update_data_links_permission_granted_creator(self, app, user, preprint, url):
        data_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        preprint.has_data_links = 'available'
        preprint.save()
        self.assert_permission(app, url, user, {'data_links': data_links}, 200)

    def test_update_data_links_invalid_payload(self, app, user, url):
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'data_links': 'maformed payload'})
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "str".'

    def test_update_data_links_invalid_url(self, app, user, preprint, url):
        preprint.has_data_links = 'available'
        preprint.save()
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'data_links': ['thisaintright']})
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Enter a valid URL.'

    # Testing permissions for updating has_prereg_links
    def test_update_has_prereg_links_permission_denied(self, app, read_contrib, url):
        self.assert_permission(app, url, read_contrib, {'has_prereg_links': 'available'}, 403)

    def test_update_has_prereg_links_permission_granted_write(self, app, write_contrib, url):
        self.assert_permission(app, url, write_contrib, {'has_prereg_links': 'available'}, 200)

    def test_update_has_prereg_links_permission_granted_admin(self, app, admin_contrib, url):
        self.assert_permission(app, url, admin_contrib, {'has_prereg_links': 'available'}, 200)

    def test_update_has_prereg_links_permission_granted_creator(self, app, user, url):
        self.assert_permission(app, url, user, {'has_prereg_links': 'available'}, 200)

    # Testing permissions for updating prereg_links
    def test_update_prereg_links_permission_denied(self, app, read_contrib, url):
        prereg_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        self.assert_permission(app, url, read_contrib, {'prereg_links': prereg_links}, 403)

    def test_update_prereg_links_permission_granted_write(self, app, write_contrib, preprint, url):
        prereg_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        preprint.has_prereg_links = 'available'
        preprint.save()
        self.assert_permission(app, url, write_contrib, {'prereg_links': prereg_links}, 200)

    def test_update_prereg_links_permission_granted_admin(self, app, admin_contrib, preprint, url):
        prereg_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        preprint.has_prereg_links = 'available'
        preprint.save()
        self.assert_permission(app, url, admin_contrib, {'prereg_links': prereg_links}, 200)

    def test_update_prereg_links_permission_granted_creator(self, app, user, preprint, url):
        prereg_links = ['http://www.JasonKelce.com', 'http://www.ItsTheWholeTeam.com/']
        preprint.has_prereg_links = 'available'
        preprint.save()
        self.assert_permission(app, url, user, {'prereg_links': prereg_links}, 200)

    def test_update_prereg_links_invalid_payload(self, app, user, url):
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'prereg_links': 'maformed payload'})
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "str".'

    def test_update_prereg_links_invalid_url(self, app, user, preprint, url):
        preprint.has_prereg_links = 'available'
        preprint.save()
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'prereg_links': ['thisaintright']})
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Enter a valid URL.'

    def test_update_prereg_link_info_fail_prereg_links(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'prereg_link_info': 'prereg_designs'})
        preprint.has_prereg_links = 'no'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot edit this field while your prereg links availability is set to false or is unanswered.'

    def test_update_prereg_link_info_success(self, app, user, preprint, url):
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'prereg_link_info': 'prereg_designs'})
        preprint.has_prereg_links = 'available'
        preprint.save()
        res = app.patch_json_api(url, update_payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['prereg_link_info'] == 'prereg_designs'
        preprint.reload()
        assert preprint.prereg_link_info == 'prereg_designs'
        log = preprint.logs.first()
        assert log.action == PreprintLog.UPDATE_PREREG_LINKS_INFO
        assert log.params == {'user': user._id, 'preprint': preprint._id}

    def test_update_prereg_link_info_invalid_payload(self, app, user, url):
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'prereg_link_info': 'maformed payload'})
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"maformed payload" is not a valid choice.'

    def test_no_prereg_links_clears_links(self, app, user, preprint, url):
        preprint.has_prereg_links = 'available'
        preprint.prereg_links = ['http://example.com']
        preprint.prereg_link_info = 'prereg_analysis'
        preprint.save()
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'has_prereg_links': 'no'})
        res = app.patch_json_api(url, update_payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['has_prereg_links'] == 'no'
        assert res.json['data']['attributes']['prereg_links'] == []
        assert not res.json['data']['attributes']['prereg_link_info']

    def test_no_data_links_clears_links(self, app, user, preprint, url):
        preprint.has_data_links = 'available'
        preprint.data_links = ['http://www.apple.com']
        preprint.save()
        update_payload = build_preprint_update_payload(node_id=user._id, attributes={'has_data_links': 'no'})
        res = app.patch_json_api(url, update_payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['has_data_links'] == 'no'
        assert res.json['data']['attributes']['data_links'] == []

    def test_sloan_updates(self, app, user, preprint, url):
        preprint.has_prereg_links = 'available'
        preprint.prereg_links = ['http://no-sf.io']
        preprint.prereg_link_info = 'prereg_designs'
        preprint.save()
        update_payload = build_preprint_update_payload(
            node_id=preprint._id,
            attributes={
                'has_prereg_links': 'available',
                'prereg_link_info': 'prereg_designs',
                'prereg_links': ['http://osf.io'],
            }
        )
        app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        logs = preprint.logs.all().values_list('action', 'params')
        assert logs.count() == 3
        assert logs.latest() == ('prereg_links_updated', {'user': user._id, 'preprint': preprint._id})

        update_payload = build_preprint_update_payload(
            node_id=preprint._id,
            attributes={
                'has_prereg_links': 'no',
                'why_no_prereg': 'My dog ate it.'
            }
        )
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['has_prereg_links'] == 'no'
        assert res.json['data']['attributes']['why_no_prereg'] == 'My dog ate it.'
        preprint.refresh_from_db()
        assert preprint.has_prereg_links == 'no'
        assert preprint.why_no_prereg == 'My dog ate it.'
