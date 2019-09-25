from datetime import datetime

import pytest

from api.base.settings import API_BASE
from osf_tests.factories import AuthUserFactory


class UserProfileFixtures:

    @pytest.fixture()
    def resource_factory(self):
        raise NotImplementedError

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture
    def profile_item_one(self, user, resource_factory):
        return resource_factory(user=user)

    @pytest.fixture
    def profile_item_two(self, user, resource_factory):
        return resource_factory(user=user)

    @pytest.fixture
    def detail_url(self, user, profile_item_one, profile_type):
        return '/{}users/{}/{}/{}/'.format(API_BASE, user._id, profile_type, profile_item_one._id)

    @pytest.fixture()
    def payload(self, object_type):
        def payload(**kwargs):
            payload = {
                'data': {
                    'type': object_type,
                    'attributes': {}
                }
            }
            _id = kwargs.pop('_id', None)
            if _id:
                payload['data']['id'] = _id
            if kwargs:
                payload['data']['attributes'] = kwargs
            return payload
        return payload

    @pytest.fixture()
    def profile_type(self):
        raise NotImplementedError

    @pytest.fixture()
    def object_type(self):
        raise NotImplementedError


@pytest.mark.django_db
class UserProfileListMixin(UserProfileFixtures):

    @pytest.fixture
    def list_url(self, user, profile_type):
        raise NotImplementedError

    @pytest.fixture(autouse=True)
    def add_resources(self, user, resource_factory):
        resource_factory(user=user, institution='Institution 1')
        resource_factory(user=user, institution='Institution 2')
        resource_factory(user=user, institution='Institution 3')

    def test_user_profile_list(self, app, user, list_url, profile_type):
        # unauthorized can access
        res = app.get(list_url)
        assert res.status_code == 200

        # another authorized user can access
        other_user = AuthUserFactory()
        res = app.get(list_url, auth=other_user.auth)
        assert res.status_code == 200

        # authorized can access self
        res = app.get(list_url, auth=user.auth)
        assert res.status_code == 200

        # check institutions are returned in the correct order
        profile_object_institutions = [each['attributes']['institution'] for each in res.json['data']]
        assert len(profile_object_institutions) == 3
        assert '1' in profile_object_institutions[0]
        assert '2' in profile_object_institutions[1]
        assert '3' in profile_object_institutions[2]

        # manually reverse the order, make sure list is returned in reversed order
        user_profile_manager = getattr(user, profile_type)
        set_user_profile_order = getattr(user, 'set_user{}_order'.format(profile_type))
        user_profile_object_ids = user_profile_manager.values_list('id', flat=True)
        set_user_profile_order(user_profile_object_ids[::-1])
        res = app.get(list_url, auth=user.auth)
        profile_institutions = [each['attributes']['institution'] for each in res.json['data']]
        assert len(profile_institutions) == 3
        assert '3' in profile_institutions[0]
        assert '2' in profile_institutions[1]
        assert '1' in profile_institutions[2]


@pytest.mark.django_db
class UserProfileDetailMixin(UserProfileFixtures):

    @pytest.fixture
    def detail_url(self):
        raise NotImplementedError

    def test_get_detail(self, app, user, user_two, detail_url):
        # unauthoized can access
        res = app.get(detail_url)
        assert res.status_code == 200

        # another authorized user can access
        other_user = AuthUserFactory()
        res = app.get(detail_url, auth=other_user.auth)
        assert res.status_code == 200

        # authorized can access self
        res = app.get(detail_url, auth=user.auth)
        assert res.status_code == 200


@pytest.mark.django_db
class UserProfileCreateMixin(UserProfileFixtures):

    def test_create_profile_object_fails(self, app, list_url, user, user_two, payload):
        # no auth fails
        res = app.post_json(list_url, payload(institution='Woop!'), expect_errors=True)
        assert res.status_code == 401

        # auth but not the user fails
        res = app.post_json(list_url, payload(institution='Helloooo'), auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # wrong type fails
        wrong_type = payload(institution='Woop!')
        wrong_type['data']['type'] = 'snails'
        res = app.post_json(list_url, wrong_type, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # Institution is empty fails
        inst_empty = payload(institution=None)
        res = app.post_json(list_url, inst_empty, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # start_date no end_date but not ongoing fails
        wrong_dates = payload(institution='Well lets go', start_date='2018-01-01', end_date=None, ongoing=False)
        res = app.post_json(list_url, wrong_dates, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # end_date but no start_date fails
        wrong_dates = payload(institution='Yeah!', end_date='2018-01-01', start_date=None)
        res = app.post_json(list_url, wrong_dates, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # end_date before start_date fails
        flopped_dates = payload(institution='What', start_date='2019-01-01', end_date='2018-01-01')
        res = app.post_json(list_url, flopped_dates, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # ongoing with start and end date fails
        not_really_ongoing = payload(institution='Yo', start_date='2018-01-01', end_date='2019-01-01', ongoing=True)
        res = app.post_json(list_url, not_really_ongoing, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_create_profile_object(self, app, list_url, user, payload, profile_type):
        user_profile_object_manager = getattr(user, profile_type)

        # test create with just institution
        new_inst_name = 'Tundra Town'
        just_inst = payload(institution=new_inst_name)
        res = app.post_json(list_url, just_inst, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['institution'] == new_inst_name
        user.reload()
        assert new_inst_name in user_profile_object_manager.values_list('institution', flat=True)

        # test create with start date and no end date and ongoing
        new_name = 'Blundra Town'
        new_start = '2018-01-01'
        start_date = payload(institution=new_name, start_date=new_start, ongoing=True)
        res = app.post_json(list_url, start_date, auth=user.auth)
        assert res.status_code == 201
        assert new_name == res.json['data']['attributes']['institution'] == new_name
        user.reload()
        new_inst = user_profile_object_manager.get(institution=new_name)
        assert new_inst.start_date == datetime.strptime(new_start, '%Y-%m-%d').date()
        assert new_inst.end_date is None
        assert new_inst.ongoing is True

        # test create with start and end dates
        new_name = 'Scundra Town'
        new_end = str(datetime.now().year + 1) + '-12-01'
        start_date = payload(institution=new_name, start_date=new_start, end_date=new_end, ongoing=False)
        res = app.post_json(list_url, start_date, auth=user.auth)
        assert res.status_code == 201
        assert new_name == res.json['data']['attributes']['institution'] == new_name
        user.reload()
        new_inst = user_profile_object_manager.get(institution=new_name)
        assert new_inst.start_date == datetime.strptime(new_start, '%Y-%m-%d').date()
        assert new_inst.end_date == datetime.strptime(new_end, '%Y-%m-%d').date()
        assert new_inst.ongoing is False


@pytest.mark.django_db
class UserProfileUpdateMixin(UserProfileFixtures):

    def test_profile_object_update_fails(self, app, detail_url, profile_item_one, profile_item_two, user, user_two, payload):
        standard_payload = payload(_id=profile_item_one._id, degree='Tundra Love', department='Dogs')

        # no auth fails
        res = app.post_json(detail_url, standard_payload, expect_errors=True)
        assert res.status_code == 401

        # auth but not the user fails
        res = app.put_json_api(detail_url, standard_payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # wrong type fails
        wrong_type = payload(_id=profile_item_one._id, institution='Woop!')
        wrong_type['data']['type'] = 'snails'
        res = app.put_json_api(detail_url, wrong_type, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # mismatched id fails
        wrong_id = payload(_id=profile_item_two._id, institution='Woop!')
        res = app.put_json_api(detail_url, wrong_id, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # Institution is empty fails
        inst_empty = payload(_id=profile_item_one._id, institution=None)
        res = app.put_json_api(detail_url, inst_empty, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # start_date no end_date but not ongoing fails
        wrong_dates = payload(_id=profile_item_one._id, start_date='2018-01-01', end_date=None, ongoing=False)
        res = app.put_json_api(detail_url, wrong_dates, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # end_date but no start_date fails
        wrong_dates = payload(_id=profile_item_one._id, end_date='2018-01-01', start_date=None)
        res = app.put_json_api(detail_url, wrong_dates, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # ongoing with start and end date fails
        not_really_ongoing = payload(_id=profile_item_one._id, start_date='2018-01-01', end_date='2019-01-01', ongoing=True)
        res = app.put_json_api(detail_url, not_really_ongoing, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_profile_object_update_succeeds(self, app, detail_url, profile_item_one, user, payload):
        # test update institution
        new_inst = 'Dogland'
        inst_payload = payload(_id=profile_item_one._id, institution=new_inst)
        res = app.put_json_api(detail_url, inst_payload, auth=user.auth)
        profile_item_one.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['institution'] == new_inst
        assert profile_item_one.institution == new_inst


@pytest.mark.django_db
class UserProfileRelationshipMixin(UserProfileFixtures):

    @pytest.fixture()
    def url(self, user, profile_type):
        raise NotImplementedError

    @pytest.fixture()
    def user_profile_object_manager(self, user, profile_type):
        return getattr(user, profile_type)

    @pytest.fixture()
    def relationship_payload(self, profile_item_one, object_type):
        return {
            'data': [
                {'type': object_type, 'id': profile_item_one._id}
            ]
        }

    def test_get(self, app, user, profile_item_one, profile_item_two, url, profile_type):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        links = res.json['links']
        assert links['self'] == '{}relationships/{}/'.format(user.absolute_api_v2_url, profile_type)
        assert links['html'] == '{}{}/'.format(user.absolute_api_v2_url, profile_type)

        ids = [result['id'] for result in res.json['data']]
        assert profile_item_one._id in ids
        assert profile_item_two._id in ids

        # unauthorized can access
        res = app.get(url)
        ids = [result['id'] for result in res.json['data']]
        assert profile_item_one._id in ids
        assert profile_item_one._id in ids

    def test_update_order(self, app, url, user, profile_item_one, profile_item_two, relationship_payload, profile_type, object_type):
        relationship_payload['data'].insert(0, {'type': object_type, 'id': profile_item_two._id})
        res = app.patch_json_api(url, relationship_payload, auth=user.auth)
        assert res.status_code == 200

        ids = [result['id'] for result in res.json['data']]
        assert ids[0] == profile_item_two._id
        assert ids[1] == profile_item_one._id

    def test_delete(self, app, user, profile_item_one, profile_item_two, url, relationship_payload, user_profile_object_manager):
        res = app.delete_json_api(url, relationship_payload, auth=user.auth)
        assert res.status_code == 204

        user.reload()

        ids = list(user_profile_object_manager.values_list('_id', flat=True))
        assert profile_item_one._id not in ids
        assert profile_item_two._id in ids

    def test_delete_multiple(self, app, user, profile_item_one, profile_item_two, url, relationship_payload, object_type, profile_type):
        relationship_payload['data'].append({'type': object_type, 'id': profile_item_two._id})
        res = app.delete_json_api(url, relationship_payload, auth=user.auth)
        assert res.status_code == 204

        user.reload()
        user_profile_object_manager = getattr(user, profile_type)
        ids = list(user_profile_object_manager.values_list('_id', flat=True))
        assert profile_item_one._id not in ids
        assert profile_item_two._id not in ids

    def test_profile_relationship_errors(self, app, user, user_two, profile_item_one, profile_item_two, url, relationship_payload, object_type):
        # wrong type fails
        wrong_payload = relationship_payload.copy()
        wrong_payload['data'][0]['type'] = 'cowabunga'
        res = app.patch_json_api(url, wrong_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # patch with no auth fails
        res = app.patch_json_api(url, relationship_payload, expect_errors=True)
        assert res.status_code == 401

        # patch with wrong auth fails
        res = app.patch_json_api(url, relationship_payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # delete with no auth fails
        res = app.delete_json_api(url, relationship_payload, expect_errors=True)
        assert res.status_code == 401

        # delete with wrong auth fails
        res = app.delete_json_api(url, relationship_payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # test id not found
        wrong_id_payload = relationship_payload.copy()
        wrong_id_payload['data'][0]['id'] = 'thisisnotreal'
        res = app.delete_json_api(url, wrong_id_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

        # test misformed payload fails
        data_not_an_array = {'data': {'type': object_type, 'id': profile_item_one._id}}
        res = app.patch_json_api(url, data_not_an_array, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # test no_type_field fails
        no_type_zone = relationship_payload.copy()
        del(no_type_zone['data'][0]['type'])
        res = app.patch_json_api(url, no_type_zone, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # test with_no_id_field fails
        no_id_zone = relationship_payload.copy()
        del(no_id_zone['data'][0]['id'])
        res = app.patch_json_api(url, no_id_zone, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
