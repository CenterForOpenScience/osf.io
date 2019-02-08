import pytest

from api.base.settings import API_BASE
from osf_tests.factories import AuthUserFactory, EducationFactory


@pytest.fixture
def user():
    return AuthUserFactory()

@pytest.fixture
def user_two():
    return AuthUserFactory()

@pytest.fixture
def education_one(user):
    return EducationFactory(user=user)

@pytest.fixture
def education_two(user):
    return EducationFactory(user=user)

@pytest.fixture
def list_url(user):
    return '/{}users/{}/education/'.format(API_BASE, user._id)

@pytest.fixture
def detail_url(user, education_one):
    return '/{}users/{}/education/{}/'.format(API_BASE, user._id, education_one._id)

@pytest.fixture()
def payload():
    def payload(**kwargs):
        payload = {
            'data': {
                'type': 'education',
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


@pytest.mark.django_db
class TestUserEducationList:

    @pytest.fixture(autouse=True)
    def add_education(self, user):
        EducationFactory(user=user, institution='Institution 1')
        EducationFactory(user=user, institution='Institution 2')
        EducationFactory(user=user, institution='Institution 3')

    def test_user_education(self, app, user, list_url):
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
        education_institutions = [each['attributes']['institution'] for each in res.json['data']]
        assert len(education_institutions) == 3
        assert '1' in education_institutions[0]
        assert '2' in education_institutions[1]
        assert '3' in education_institutions[2]

        # manually reverse the order, make sure list is returned in reversed order
        user_education_ids = user.education.values_list('id', flat=True)
        user.set_education_order(user_education_ids[::-1])
        res = app.get(list_url, auth=user.auth)
        education_institutions = [each['attributes']['institution'] for each in res.json['data']]
        assert len(education_institutions) == 3
        assert '3' in education_institutions[0]
        assert '2' in education_institutions[1]
        assert '1' in education_institutions[2]


@pytest.mark.django_db
class TestEducationDetail:

    def test_get_education_detail(self, app, user, detail_url, education_one):
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
class TestUerEducationCreate:

    def test_create_education_fails(self, app, list_url, user, user_two, payload):
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

        # ongoing with start and end date fails
        not_really_ongoing = payload(institution='Yo', start_date='2018-01-01', end_date='2019-01-01', ongoing=True)
        res = app.post_json(list_url, not_really_ongoing, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_create_education(self, app, list_url, user):
        # TODO - do this
        pass


@pytest.mark.django_db
class TestUserEducationUpdate:

    def test_education_update_fails(self, app, detail_url, education_one, education_two, user, user_two, payload):
        standard_payload = payload(_id=education_one._id, degree='Tundra Love', department='Dogs')

        # no auth fails
        res = app.post_json(detail_url, standard_payload, expect_errors=True)
        assert res.status_code == 401

        # auth but not the user fails
        res = app.put_json_api(detail_url, standard_payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # wrong type fails
        wrong_type = payload(_id=education_one._id)
        wrong_type['data']['type'] = 'snails'
        res = app.put_json_api(detail_url, wrong_type, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # mismatched id fails
        wrong_id = payload(_id=education_two._id)
        res = app.put_json_api(detail_url, wrong_id, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # Institution is empty fails
        inst_empty = payload(_id=education_one._id, institution=None)
        res = app.put_json_api(detail_url, inst_empty, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # start_date no end_date but not ongoing fails
        wrong_dates = payload(_id=education_one._id, start_date='2018-01-01', end_date=None, ongoing=False)
        res = app.put_json_api(detail_url, wrong_dates, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # end_date but no start_date fails
        wrong_dates = payload(_id=education_one._id, end_date='2018-01-01', start_date=None)
        res = app.put_json_api(detail_url, wrong_dates, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # ongoing with start and end date fails
        not_really_ongoing = payload(_id=education_one._id, start_date='2018-01-01', end_date='2019-01-01', ongoing=True)
        res = app.put_json_api(detail_url, not_really_ongoing, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_education_update_succeeds(self, app, detail_url, education_one, user, payload):
        # test update institution
        new_inst = 'Dogland'
        inst_payload = payload(_id=education_one._id, institution=new_inst)
        res = app.put_json_api(detail_url, inst_payload, auth=user.auth)
        education_one.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['institution'] == new_inst
        assert education_one.institution == new_inst


@pytest.mark.django_db
class TestUserEducationRelationship:

    @pytest.fixture
    def education_one(self, user):
        return EducationFactory(user=user, institution='Institution 1')

    @pytest.fixture
    def education_two(self, user):
        return EducationFactory(user=user, institution='Institution 2')

    @pytest.fixture
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture
    def payload(self, education_one):
        return {
            'data': [
                {'type': 'education', 'id': education_one._id}
            ]
        }

    @pytest.fixture()
    def url(self, user):
        return '/{}users/{}/relationships/education/'.format(API_BASE, user._id)

    def test_get(self, app, user, education_one, education_two, url):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        links = res.json['links']
        assert links['self'] == '{}relationships/education/'.format(user.absolute_api_v2_url)
        assert links['html'] == '{}education/'.format(user.absolute_api_v2_url)

        ids = [result['id'] for result in res.json['data']]
        assert education_one._id in ids
        assert education_two._id in ids

        # unauthorized can access
        res = app.get(url)
        ids = [result['id'] for result in res.json['data']]
        assert education_one._id in ids
        assert education_one._id in ids

    def test_update_order(self, app, url, user, education_one, education_two, payload):
        payload['data'].insert(0, {'type': 'education', 'id': education_two._id})
        res = app.patch_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200

        ids = [result['id'] for result in res.json['data']]
        assert ids[0] == education_two._id
        assert ids[1] == education_one._id

    def test_delete(self, app, user, education_one, education_two, url, payload):
        res = app.delete_json_api(url, payload, auth=user.auth)
        assert res.status_code == 204

        user.reload()
        ids = list(user.education.values_list('_id', flat=True))
        assert education_one._id not in ids
        assert education_two._id in ids

    def test_delete_multiple(self, app, user, education_one, education_two, url, payload):
        payload['data'].append({'type': 'education', 'id': education_two._id})
        res = app.delete_json_api(url, payload, auth=user.auth)
        assert res.status_code == 204

        user.reload()
        ids = list(user.education.values_list('_id', flat=True))
        assert education_one._id not in ids
        assert education_two._id not in ids

    def test_education_relationship_errors(self, app, user, user_two, education_one, education_two, url, payload):
        # wrong type fails
        wrong_payload = payload.copy()
        wrong_payload['data'][0]['type'] = 'cowabunga'
        res = app.patch_json_api(url, wrong_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

        # patch with no auth fails
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # patch with wrong auth fails
        res = app.patch_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # delete with no auth fails
        res = app.delete_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # delete with wrong auth fails
        res = app.delete_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # test id not found
        wrong_id_payload = payload.copy()
        wrong_id_payload['data'][0]['id'] = 'thisisnotreal'
        res = app.delete_json_api(url, wrong_id_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

        # test misformed payload fails
        data_not_an_array = {'data': {'type': 'education', 'id': education_one._id}}
        res = app.patch_json_api(url, data_not_an_array, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        #   test_attempt_with_no_type_field
        no_type_zone = payload.copy()
        del(no_type_zone['data'][0]['type'])
        res = app.patch_json_api(url, no_type_zone, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        #   test_attempt_with_no_id_field
        no_id_zone = payload.copy()
        del(no_id_zone['data'][0]['id'])
        res = app.patch_json_api(url, no_id_zone, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
