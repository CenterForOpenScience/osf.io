import pytest

from api.preprint_providers.permissions import GroupHelper
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
)


@pytest.mark.django_db
class PreprintsListFilteringMixin(object):

    @pytest.fixture()
    def user(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_one(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_two(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_three(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_one(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_two(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_three(self):
        raise NotImplementedError

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def subject_one(self):
        return SubjectFactory(text='First Subject')

    @pytest.fixture()
    def subject_two(self):
        return SubjectFactory(text='Second Subject')

    @pytest.fixture()
    def preprint_one(self, user, project_one, provider_one, subject_one):
        preprint_one = PreprintFactory(creator=user, project=project_one, provider=provider_one, subjects=[[subject_one._id]])
        preprint_one.original_publication_date = '2013-12-25 10:09:08.070605+00:00'
        preprint_one.save()
        return preprint_one

    @pytest.fixture()
    def preprint_two(self, user, project_two, provider_two, subject_two):
        preprint_two = PreprintFactory(creator=user, project=project_two, filename='howto_reason.txt', provider=provider_two, subjects=[[subject_two._id]])
        preprint_two.created = '2013-12-11 10:09:08.070605+00:00'
        preprint_two.date_published = '2013-12-11 10:09:08.070605+00:00'
        preprint_two.original_publication_date = '2013-12-11 10:09:08.070605+00:00'
        preprint_two.save()
        return preprint_two

    @pytest.fixture()
    def preprint_three(self, user, project_three, provider_three, subject_one, subject_two):
        preprint_three = PreprintFactory(creator=user, project=project_three, filename='darn_reason.txt', provider=provider_three, subjects=[[subject_one._id], [subject_two._id]])
        preprint_three.created = '2013-12-11 10:09:08.070605+00:00'
        preprint_three.date_published = '2013-12-11 10:09:08.070605+00:00'
        preprint_three.original_publication_date = '2013-12-11 10:09:08.070605+00:00'
        preprint_three.is_published = False
        preprint_three.save()
        return preprint_three

    @pytest.fixture()
    def provider_url(self, url):
        return '{}filter[provider]='.format(url)

    @pytest.fixture()
    def id_url(self, url):
        return '{}filter[id]='.format(url)

    @pytest.fixture()
    def created_url(self, url):
        return '{}filter[date_created]='.format(url)

    @pytest.fixture()
    def date_modified_url(self, url):
        return '{}filter[date_modified]='.format(url)

    @pytest.fixture()
    def date_published_url(self, url):
        return '{}filter[date_published]='.format(url)

    @pytest.fixture()
    def original_publication_date_url(self, url):
        return '{}filter[original_publication_date]='.format(url)

    @pytest.fixture()
    def is_published_url(self, url):
        return '{}filter[is_published]='.format(url)

    @pytest.fixture()
    def is_published_and_modified_url(self, url):
        return '{}filter[is_published]=true&filter[date_created]=2013-12-11'.format(url)

    @pytest.fixture()
    def node_is_public_url(self, url):
        return '{}filter[node_is_public]='.format(url)

    @pytest.fixture()
    def has_subject(self, url):
        return '{}filter[subjects]='.format(url)

    def test_provider_filter_null(self, app, user, provider_url):
        expected = []
        res = app.get('{}null'.format(provider_url), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_id_filter_null(self, app, user, id_url):
        expected = []
        res = app.get('{}null'.format(id_url), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_id_filter_equals_returns_one(self, app, user, preprint_two, id_url):
        expected = [preprint_two._id]
        res = app.get('{}{}'.format(id_url, preprint_two._id), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_none(self, app, user, created_url):
        expected = []
        res = app.get('{}{}'.format(created_url, '2015-11-15 10:09:08.070605+00:00'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_one(self, app, user, preprint_one, created_url):
        expected = [preprint_one._id]
        res = app.get('{}{}'.format(created_url, preprint_one.created), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_multiple(self, app, user, preprint_two, preprint_three, created_url):
        expected = set([preprint_two._id, preprint_three._id])
        res = app.get('{}{}'.format(created_url, preprint_two.created), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_date_modified_filter_equals_returns_none(self, app, user, date_modified_url):
        expected = []
        res = app.get('{}{}'.format(date_modified_url, '2015-11-15 10:09:08.070605+00:00'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    # This test was causing problems because modifying anything caused set modified dates to update to current date
    # This test could hypothetically fail if the time between fixture creations splits a day (e.g., midnight)
    def test_date_modified_filter_equals_returns_multiple(self, app, user, preprint_one, preprint_two, preprint_three, date_modified_url):
        expected = set([preprint_one._id, preprint_two._id, preprint_three._id])
        res = app.get('{}{}'.format(date_modified_url, preprint_one.modified), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_date_published_filter_equals_returns_none(self, app, user, date_published_url):
        expected = []
        res = app.get('{}{}'.format(date_published_url, '2015-11-15 10:09:08.070605+00:00'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_published_filter_equals_returns_one(self, app, user, preprint_one, date_published_url):
        expected = [preprint_one._id]
        res = app.get('{}{}'.format(date_published_url, preprint_one.date_published), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_published_filter_equals_returns_multiple(self, app, user, preprint_two, preprint_three, date_published_url):
        expected = set([preprint_two._id, preprint_three._id])
        res = app.get('{}{}'.format(date_published_url, preprint_two.date_published), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_original_publication_date_filter_equals_returns_none(self, app, user, original_publication_date_url):
        expected = []
        res = app.get('{}{}'.format(original_publication_date_url, '2015-11-15 10:09:08.070605+00:00'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_original_publication_date_filter_equals_returns_one(self, app, user, preprint_one, original_publication_date_url):
        expected = [preprint_one._id]
        res = app.get('{}{}'.format(original_publication_date_url, preprint_one.original_publication_date), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_original_publication_date_filter_equals_returns_multiple(self, app, user, preprint_two, preprint_three, original_publication_date_url):
        expected = set([preprint_two._id, preprint_three._id])
        res = app.get('{}{}'.format(original_publication_date_url, preprint_two.original_publication_date), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_is_published_false_filter_equals_returns_one(self, app, user, preprint_three, is_published_url):
        expected = [preprint_three._id]
        res = app.get('{}{}'.format(is_published_url, 'false'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_is_published_true_filter_equals_returns_multiple(self, app, user, preprint_one, preprint_two, is_published_url):
        expected = set([preprint_one._id, preprint_two._id])
        res = app.get('{}{}'.format(is_published_url, 'true'), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_multiple_filters_returns_one(self, app, user, preprint_two, is_published_and_modified_url):
        expected = set([preprint_two._id])
        res = app.get(is_published_and_modified_url,
            auth=user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_subject_filter_using_id(self, app, user, subject_one, preprint_one, preprint_three, has_subject):
        expected = set([preprint_one._id, preprint_three._id])
        res = app.get('{}{}'.format(has_subject, subject_one._id),
            auth=user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_subject_filter_using_text(self, app, user, subject_one, preprint_one, preprint_three, has_subject):
        expected = set([preprint_one._id, preprint_three._id])
        res = app.get('{}{}'.format(has_subject, subject_one.text),
            auth=user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_unknows_subject_filter(self, app, user, has_subject):
        res = app.get('{}notActuallyASubjectIdOrTestMostLikely'.format(has_subject),
            auth=user.auth
        )
        assert len(res.json['data']) == 0

    def test_node_is_public_filter(self, app, user, preprint_one, preprint_two, preprint_three, node_is_public_url):
        preprint_one.node.is_public = False
        preprint_one.node.save()
        preprint_two.node.is_public = True
        preprint_two.node.save()
        preprint_three.node.is_public = True
        preprint_three.node.save()

        preprints = [preprint_one, preprint_two, preprint_three]

        res = app.get('{}{}'.format(node_is_public_url, 'false'), auth=user.auth)
        expected = set([p._id for p in preprints if not p.node.is_public])
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

        res = app.get('{}{}'.format(node_is_public_url, 'true'), auth=user.auth)
        expected = set([p._id for p in preprints if p.node.is_public])
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    @pytest.mark.parametrize('group_name', ['admin', 'moderator'])
    def test_permissions(self, app, url, preprint_one, preprint_two, preprint_three, group_name):
        another_user = AuthUserFactory()
        preprints = (preprint_one, preprint_two, preprint_three)

        for preprint in preprints:
            preprint.is_published = False
            preprint.save()

        def actual():
            res = app.get(url, auth=another_user.auth)
            return set([preprint['id'] for preprint in res.json['data']])

        expected = set()
        assert expected == actual()

        for preprint in preprints:
            another_user.groups.add(GroupHelper(preprint.provider).get_group(group_name))
            expected.update([p._id for p in preprints if p.provider_id == preprint.provider_id])
            assert expected == actual()
