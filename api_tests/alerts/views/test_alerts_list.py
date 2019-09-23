import pytest
from rest_framework import status as http_status

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    DismissedAlertFactory,
)

url_alerts_list = '/{}alerts/'.format(API_BASE)

@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()

@pytest.mark.django_db
class TestDismissedAlertList:

    @pytest.fixture(autouse=True)
    def alerts_user_one(self, user_one):
        for i in range(3):
            DismissedAlertFactory(
                user=user_one,
                location='solar/eclipse{}/'.format(i),
                _id='solarEclipse{}'.format(i))

    def test_dismissed_alerts_list(self, app, user_one, user_two):

        alert_id = 'githubOrgs'
        alert_location = 'jc3vf/settings/'
        params = {
            'data': {
                'type': 'alerts',
                'id': alert_id,
                'attributes': {
                    'location': alert_location
                }
            }
        }

        # test_user_dismiss_alert
        res = app.post_json_api(url_alerts_list, params, auth=user_one.auth)
        assert res.status_code == http_status.HTTP_201_CREATED
        assert res.json['data']['id'] == alert_id
        assert res.json['data']['attributes']['location'] == alert_location

        # test_alerts_list_read_success
        res = app.get(url_alerts_list, auth=user_one.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert len(res.json['data']) == 4
        assert res.json['links']['meta']['total'] == len(res.json['data'])

        # test_alerts_list_id_filter
        url = '{}?filter[id]={}'.format(url_alerts_list, alert_id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert len(res.json['data']) == 1
        res_data = res.json['data'][0]
        assert res_data['attributes']['location'] == alert_location
        assert res_data['id'] == alert_id

        # test_alerts_list_location_filter
        url = '{}?filter[location]={}'.format(url_alerts_list, alert_location)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert len(res.json['data']) == 1
        res_data = res.json['data'][0]
        assert res_data['attributes']['location'] == alert_location
        assert res_data['id'] == alert_id

        # test_alerts_create_no_auth_gets_403
        res = app.post_json_api(url_alerts_list, params, expect_errors=True)
        assert res.status_code == http_status.HTTP_401_UNAUTHORIZED

        # test_alerts_read_user_only_gets_own_alerts
        res = app.get(url_alerts_list, auth=user_two.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert not res.json['data']

        # test_alerts_create_with_bad_data_gets_400
        params_empty_id = params.copy()
        params_empty_id['data']['id'] = ''
        res = app.post_json_api(url_alerts_list, params_empty_id, auth=user_one.auth, expect_errors=True)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

        params_empty_loc = params.copy()
        params_empty_loc['data']['attributes']['location'] = ''
        res = app.post_json_api(url_alerts_list, params_empty_loc, auth=user_one.auth, expect_errors=True)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

        params_extra_attr = params.copy()
        params_extra_attr['data']['attributes']['what'] = 'extra'
        res = app.post_json_api(url_alerts_list, params_extra_attr, auth=user_one.auth, expect_errors=True)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST
