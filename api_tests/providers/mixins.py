import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    SubjectFactory,
    AuthUserFactory,
    CollectionFactory,
)
from osf.models import NodeLicense, RegistrationProvider


class ProviderMixinBase(object):
    @property
    def provider_class(self):
        raise NotImplementedError

@pytest.mark.django_db
class ProviderExistsMixin(ProviderMixinBase):
    # Regression for https://openscience.atlassian.net/browse/OSF-7621

    @pytest.fixture()
    def fake_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_url_two(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_list_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_list_url_fake(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider(self):
        return self.provider_class()

    @pytest.fixture()
    def provider_two(self):
        return self.provider_class()

    def test_provider_exists(self, app, provider_url, fake_url, provider_list_url, provider_list_url_fake):
        detail_res = app.get(provider_url)
        assert detail_res.status_code == 200

        licenses_res = app.get('{}licenses/'.format(provider_url))
        assert licenses_res.status_code == 200

        res = app.get(provider_list_url)
        assert res.status_code == 200

        taxonomies_res = app.get('{}taxonomies/'.format(provider_url))
        assert taxonomies_res.status_code == 200

        #   test_preprint_provider_does_not_exist_returns_404
        detail_res = app.get(fake_url, expect_errors=True)
        assert detail_res.status_code == 404

        licenses_res = app.get(
            '{}licenses/'.format(fake_url),
            expect_errors=True)
        assert licenses_res.status_code == 404

        res = app.get(
            provider_list_url_fake,
            expect_errors=True)
        assert res.status_code == 404

        taxonomies_res = app.get(
            '{}taxonomies/'.format(fake_url),
            expect_errors=True)
        assert taxonomies_res.status_code == 404

    def test_has_highlighted_subjects_flag(
            self, app, provider,
            provider_two, provider_url, provider_url_two):
        SubjectFactory(
            provider=provider,
            text='A', highlighted=True)
        SubjectFactory(provider=provider_two, text='B')

        res = app.get(provider_url)
        assert res.status_code == 200
        res_subjects = res.json['data']['relationships']['highlighted_taxonomies']
        assert res_subjects['links']['related']['meta']['has_highlighted_subjects'] is True

        res = app.get(provider_url_two)
        assert res.status_code == 200
        res_subjects = res.json['data']['relationships']['highlighted_taxonomies']
        assert res_subjects['links']['related']['meta']['has_highlighted_subjects'] is False


@pytest.mark.django_db
class ProviderSubjectsMixin(ProviderMixinBase):
    """
    Subject Hierarchy
    +-----------------------------+
    |                             |
    |      +-------->B+----->F    |
    |      |                      |
    |  A+----------->C            |
    |      |                      |
    |      +-------->D+----->G    |
    |                             |
    |  H+------>I+----->J         |
    |            |                |
    |            +----->K         |
    |                             |
    |  L+------>M+----->N         |
    |            |                |
    |            +------->E       |
    |                             |
    |  O                          |
    |                             |
    |  Z                          |
    |                             |
    |  Other Sub                  |
    +-----------------------------+
    """
    @pytest.fixture(autouse=True)
    def subA(self):
        return SubjectFactory(text='A')

    @pytest.fixture(autouse=True)
    def subB(self, subA):
        return SubjectFactory(text='B', parent=subA)

    @pytest.fixture(autouse=True)
    def subC(self, subA):
        return SubjectFactory(text='C', parent=subA)

    @pytest.fixture(autouse=True)
    def subD(self, subA):
        return SubjectFactory(text='D', parent=subA)

    @pytest.fixture(autouse=True)
    def subF(self, subB):
        return SubjectFactory(text='F', parent=subB)

    @pytest.fixture(autouse=True)
    def subG(self, subD):
        return SubjectFactory(text='G', parent=subD)

    @pytest.fixture(autouse=True)
    def subH(self):
        return SubjectFactory(text='H')

    @pytest.fixture(autouse=True)
    def subI(self, subH):
        return SubjectFactory(text='I', parent=subH)

    @pytest.fixture(autouse=True)
    def subJ(self, subI):
        return SubjectFactory(text='J', parent=subI)

    @pytest.fixture(autouse=True)
    def subK(self, subI):
        return SubjectFactory(text='K', parent=subI)

    @pytest.fixture(autouse=True)
    def subL(self):
        return SubjectFactory(text='L')

    @pytest.fixture(autouse=True)
    def subM(self, subL):
        return SubjectFactory(text='M', parent=subL)

    @pytest.fixture(autouse=True)
    def subE(self, subM):
        return SubjectFactory(text='E', parent=subM)

    @pytest.fixture(autouse=True)
    def subN(self, subM):
        return SubjectFactory(text='N', parent=subM)

    @pytest.fixture(autouse=True)
    def subO(self):
        return SubjectFactory(text='O')

    @pytest.fixture(autouse=True)
    def subOther(self):
        return SubjectFactory(text='Other Sub')

    @pytest.fixture(autouse=True)
    def subZ(self):
        return SubjectFactory(text='Z')

    @pytest.fixture()
    def rules(self, subA, subB, subD, subH, subI, subJ, subL):
        return [
            ([subA._id, subB._id], False),
            ([subA._id, subD._id], True),
            ([subH._id, subI._id, subJ._id], True),
            ([subL._id], True)
        ]
        #  This should allow: A, B, D, G, H, I, J, L, M, N and E
        #  This should not allow: C, F, K, O

    @pytest.fixture()
    def lawless_provider(self):
        return self.provider_class()

    @pytest.fixture()
    def ruled_provider(self, rules):
        provider = self.provider_class()
        provider.subjects_acceptable = rules
        provider.save()
        return provider

    @pytest.fixture()
    def lawless_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def ruled_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def base_url(self):
        raise NotImplementedError

    def test_max_page_size(self, app, lawless_provider, base_url):
        res = app.get(base_url)
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 10

        res = app.get(base_url + '?page[size]=150')
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 150

        res = app.get(base_url + '?page[size]=2018')
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 1000

    def test_no_rules_grabs_all(self, app, lawless_url):
        res = app.get(lawless_url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 17

    def test_rules_only_grab_acceptable_subjects(self, app, ruled_url):
        res = app.get(ruled_url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 11

    def test_no_rules_with_null_parent_filter(self, app, lawless_url):
        res = app.get(lawless_url + 'filter[parents]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 6

    def test_rules_enforced_with_null_parent_filter(self, app, ruled_url):
        res = app.get(ruled_url + 'filter[parents]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'A' in texts
        assert 'H' in texts
        assert 'L' in texts
        assert 'O' not in texts

    def test_no_rules_with_parents_filter(self, app, lawless_url, subB, subI, subM):
        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert res.json['data'][0]['attributes']['text'] == 'F'

        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

    def test_rules_enforced_with_parents_filter(self, app, ruled_url, subB, subI, subM):
        res = app.get(
            ruled_url +
            'filter[parents]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 0
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'F' not in texts

        res = app.get(
            ruled_url +
            'filter[parents]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'J' in texts
        assert 'K' not in texts

        res = app.get(
            ruled_url +
            'filter[parents]={}'.format(
                subM._id))

    def test_no_rules_with_parent_filter(self, app, lawless_url, subB, subI, subM):
        res = app.get(
            lawless_url +
            'filter[parent]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert res.json['data'][0]['attributes']['text'] == 'F'

        res = app.get(
            lawless_url +
            'filter[parent]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        res = app.get(
            lawless_url +
            'filter[parent]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

    def test_rules_enforced_with_parent_filter(self, app, ruled_url, subB, subI, subM):
        res = app.get(
            ruled_url +
            'filter[parent]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 0
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'F' not in texts

        res = app.get(
            ruled_url +
            'filter[parent]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'J' in texts
        assert 'K' not in texts

        res = app.get(
            ruled_url +
            'filter[parent]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'N' in texts
        assert 'E' in texts

    def test_no_rules_with_grandparent_filter(self, app, lawless_url, subA):
        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3

    def test_rules_enforced_with_grandparent_filter(self, app, ruled_url, subA):
        res = app.get(
            ruled_url +
            'filter[parents]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'B' in texts
        assert 'D' in texts
        assert 'C' not in texts

    def test_taxonomy_other_ordering(self, app, lawless_url, subOther):
        res = app.get(lawless_url)
        assert res.json['data'][-1]['id'] == subOther._id


@pytest.mark.django_db
class ProviderSpecificSubjectsMixin(ProviderMixinBase):

    @pytest.fixture(autouse=True)
    def provider_1(self):
        return self.provider_class()

    @pytest.fixture(autouse=True)
    def provider_2(self):
        return self.provider_class()

    @pytest.fixture(autouse=True)
    def root_subject_1(self, provider_1):
        return SubjectFactory(text='R1', provider=provider_1)

    @pytest.fixture(autouse=True)
    def parent_subject_1(self, provider_1, root_subject_1):
        return SubjectFactory(text='P1', provider=provider_1, parent=root_subject_1)

    @pytest.fixture(autouse=True)
    def rootOther(self, provider_1):
        return SubjectFactory(text='Other 1', provider=provider_1)

    @pytest.fixture(autouse=True)
    def child_subject_1(self, provider_1, parent_subject_1):
        return SubjectFactory(text='C1', provider=provider_1, parent=parent_subject_1)

    @pytest.fixture(autouse=True)
    def root_subject_2(self, provider_2):
        return SubjectFactory(text='R2', provider=provider_2)

    @pytest.fixture(autouse=True)
    def parent_subject_2(self, provider_2, root_subject_2):
        return SubjectFactory(text='P2', provider=provider_2, parent=root_subject_2)

    @pytest.fixture(autouse=True)
    def child_subject_2(self, provider_2, parent_subject_2):
        return SubjectFactory(text='C2', provider=provider_2, parent=parent_subject_2)

    @pytest.fixture()
    def url_1(self):
        raise NotImplementedError

    @pytest.fixture()
    def url_2(self):
        raise NotImplementedError

    def test_mapped_subjects_are_not_shared_list(self, app, url_1, url_2):
        res_1 = app.get(url_1)
        res_2 = app.get(url_2)

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 4
        assert res_2.json['links']['meta']['total'] == 3

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) &
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 0

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) |
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 7

    def test_mapped_subjects_are_not_shared_filter(self, app, url_1, url_2, root_subject_1, root_subject_2):
        res_1 = app.get(
            url_1 +
            'filter[parent]={}'.format(
                root_subject_1._id))
        res_2 = app.get(
            url_2 +
            'filter[parent]={}'.format(
                root_subject_2._id))

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 1
        assert res_2.json['links']['meta']['total'] == 1

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) &
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 0

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) |
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 2

    def test_mapped_subjects_filter_wrong_provider(self, app, url_1, url_2, root_subject_1, root_subject_2):
        res_1 = app.get(
            url_1 +
            'filter[parent]={}'.format(
                root_subject_2))
        res_2 = app.get(
            url_2 +
            'filter[parent]={}'.format(
                root_subject_1))

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 0
        assert res_2.json['links']['meta']['total'] == 0

    def test_taxonomy_other_ordering(self, app, url_1, rootOther):
        res = app.get(url_1)
        assert res.json['data'][-1]['id'] == rootOther._id


@pytest.mark.django_db
class ProviderCustomTaxonomyMixin(ProviderMixinBase):

    @pytest.fixture()
    def osf_provider(self):
        return self.provider_class(_id='osf')

    @pytest.fixture()
    def asdf_provider(self):
        return self.provider_class(_id='asdf')

    @pytest.fixture()
    def bepress_subj(self, osf_provider):
        return SubjectFactory(text='BePress Text', provider=osf_provider)

    @pytest.fixture()
    def other_subj(self, bepress_subj, asdf_provider):
        return SubjectFactory(text='Other Text', bepress_subject=bepress_subj, provider=asdf_provider)

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    def test_taxonomy_share_title(self, app, url, osf_provider, asdf_provider, bepress_subj, other_subj):
        bepress_res = app.get(
            url.format(
                API_BASE,
                osf_provider._id))
        asdf_res = app.get(
            url.format(
                API_BASE,
                asdf_provider._id))

        assert len(bepress_res.json['data']) == len(asdf_res.json['data']) == 1
        assert bepress_res.json['data'][0]['attributes']['share_title'] == osf_provider.share_title
        assert asdf_res.json['data'][0]['attributes']['share_title'] == asdf_provider.share_title


@pytest.mark.django_db
class ProviderCustomSubjectMixin(ProviderMixinBase):

    @pytest.fixture()
    def osf_provider(self):
        return self.provider_class(_id='osf')

    @pytest.fixture()
    def asdf_provider(self):
        return self.provider_class(_id='asdf')

    @pytest.fixture()
    def bepress_subj(self, osf_provider):
        return SubjectFactory(text='BePress Text', provider=osf_provider)

    @pytest.fixture()
    def other_subj(self, bepress_subj, asdf_provider):
        return SubjectFactory(text='Other Text', bepress_subject=bepress_subj, provider=asdf_provider)

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    def test_taxonomy_share_title(self, app, url, osf_provider, asdf_provider, bepress_subj, other_subj):
        bepress_res = app.get(
            url.format(
                API_BASE,
                osf_provider._id))
        asdf_res = app.get(
            url.format(
                API_BASE,
                asdf_provider._id))

        assert len(bepress_res.json['data']) == len(asdf_res.json['data']) == 1
        assert bepress_res.json['data'][0]['attributes']['taxonomy_name'] == osf_provider.share_title
        assert asdf_res.json['data'][0]['attributes']['taxonomy_name'] == asdf_provider.share_title


@pytest.mark.django_db
class ProviderHighlightedSubjectsMixin(ProviderMixinBase):

    @pytest.fixture()
    def provider(self):
        return self.provider_class()

    @pytest.fixture()
    def subj_a(self, provider):
        return SubjectFactory(provider=provider, text='A')

    @pytest.fixture()
    def subj_aa(self, provider, subj_a):
        return SubjectFactory(provider=provider, text='AA', parent=subj_a, highlighted=True)

    @pytest.fixture()
    def url(self, provider):
        raise NotImplementedError

    def test_mapped_subjects_filter_wrong_provider(self, app, url, subj_aa):
        res = app.get(url)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == subj_aa._id


@pytest.mark.django_db
class ProviderListViewTestBaseMixin(ProviderMixinBase):

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_one(self):
        return self.provider_class(name='Sockarxiv')

    @pytest.fixture()
    def provider_two(self):
        provider = self.provider_class(name='Spotarxiv')
        provider.allow_submissions = False
        provider.domain = 'https://www.spotarxiv.com'
        provider.description = 'spots not dots'
        provider.domain_redirect_enabled = True
        provider._id = 'spot'
        provider.save()
        return provider

    def test_provider_list(
            self, app, url, user, provider_one, provider_two):
        # Test length and not auth
        res = app.get(url)
        assert res.status_code == 200
        if isinstance(provider_one, RegistrationProvider):
            assert len(res.json['data']) == 3  # 2 test provider +1 for default provider
        else:
            assert len(res.json['data']) == 2

        # Test length and auth
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        if isinstance(provider_one, RegistrationProvider):
            assert len(res.json['data']) == 3  # 2 test provider +1 for default provider
        else:
            assert len(res.json['data']) == 2

    @pytest.mark.parametrize('filter_type,filter_value', [
        ('allow_submissions', True),
        ('description', 'spots%20not%20dots'),
        ('domain', 'https://www.spotarxiv.com'),
        ('domain_redirect_enabled', True),
        ('id', 'spot'),
        ('name', 'Spotarxiv'),
    ])
    def test_provider_list_filtering(
            self, filter_type, filter_value, app, url,
            provider_one, provider_two):
        res = app.get('{}?filter[{}]={}'.format(
            url, filter_type, filter_value))
        assert res.status_code == 200
        if isinstance(provider_one, RegistrationProvider) and filter_type == 'allow_submissions':
            assert len(res.json['data']) == 2  # 1 test provider +1 for default provider
        else:
            assert len(res.json['data']) == 1

class ProviderDetailViewTestBaseMixin(ProviderExistsMixin):

    def test_provider_exists(self, app, provider_url, fake_url, provider_list_url, provider_list_url_fake):
        detail_res = app.get(provider_url)
        assert detail_res.status_code == 200

        licenses_res = app.get('{}licenses/'.format(provider_url))
        assert licenses_res.status_code == 200

        taxonomies_res = app.get('{}taxonomies/'.format(provider_url))
        assert taxonomies_res.status_code == 200

        #  test_submission_provider_does_not_exist_returns_404
        detail_res = app.get(fake_url, expect_errors=True)
        assert detail_res.status_code == 404

        licenses_res = app.get(
            '{}licenses/'.format(fake_url),
            expect_errors=True)
        assert licenses_res.status_code == 404

        res = app.get(
            provider_list_url_fake,
            expect_errors=True)
        assert res.status_code == 404

        taxonomies_res = app.get(
            '{}taxonomies/'.format(fake_url),
            expect_errors=True)
        assert taxonomies_res.status_code == 404

class ProviderSubmissionMixinBase(object):
    @property
    def submission_class(self):
        raise NotImplementedError

@pytest.mark.django_db
class ProviderSubmissionListViewTestBaseMixin(ProviderMixinBase, ProviderSubmissionMixinBase):

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def submission_provider(self, user_one):
        submission_provider = self.provider_class(creator=user_one)
        submission_provider.allow_submissions = False
        submission_provider.save()
        submission_provider.primary_collection.status_choices = ['', 'asdf', 'fdsa']
        submission_provider.primary_collection.collected_type_choices = ['', 'asdf', 'fdsa']
        submission_provider.primary_collection.save()
        return submission_provider

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def submission_one(self, user_one):
        return self.submission_class(creator=user_one)

    @pytest.fixture()
    def submission_two(self, user_one):
        return self.submission_class(creator=user_one)

    @pytest.fixture()
    def subject_one(self):
        return SubjectFactory()

    @pytest.fixture()
    def collection_with_provider(self, user_one, submission_one):
        c = CollectionFactory(creator=user_one, status_choices=['asdf'])
        c.collect_object(submission_one, user_one, status='asdf')
        return c

    @pytest.fixture()
    def collection_without_provider(self, user_one, submission_one):
        c = CollectionFactory(creator=user_one)
        c.collect_object(submission_one, user_one)
        return c

    @pytest.fixture(autouse=True)
    def primary_collection(self, submission_provider, user_one, submission_one):
        c = submission_provider.primary_collection
        c.collect_object(submission_one, user_one, status='fdsa')
        return c

    @pytest.fixture()
    def payload(self):
        def make_collection_payload(**attributes):
            return {
                'data': {
                    'type': 'collected-metadata',
                    'attributes': attributes,
                }
            }
        return make_collection_payload

    def test_no_permissions(
        self, app, primary_collection, submission_provider, collection_with_provider,
            collection_without_provider, user_one, user_two, submission_two, url, payload):
        # Private

        # Sanity Check
        assert submission_provider.allow_submissions is False

        res = app.get(url)
        assert res.status_code == 200
        assert len(res.json['data']) == 1

        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=submission_two._id, status='asdf'),
            expect_errors=True)
        assert res.status_code == 401

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=submission_two._id, status='asdf'),
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403

        # Public, accepting submissions
        submission_provider.allow_submissions = True
        submission_provider.save()
        primary_collection.is_public = True
        primary_collection.save()
        res = app.get(url)
        assert len(res.json['data']) == 1
        assert res.status_code == 200

        res = app.get(url, auth=user_two.auth)
        assert len(res.json['data']) == 1
        assert res.status_code == 200

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=submission_two._id, status='asdf'),
            expect_errors=True)
        assert res.status_code == 401

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=submission_two._id, status='asdf'),
            auth=user_two.auth,
            expect_errors=True)
        # Neither collection perms nor project perms
        assert res.status_code == 403

        submission_three = self.submission_class(creator=user_two)  # has referent perm

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=submission_three._id, status='asdf'),
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 201

        assert not (collection_with_provider.guid_links.all() | collection_without_provider.guid_links.all()).filter(_id=submission_three._id).exists()
        assert primary_collection.guid_links.filter(_id=submission_three._id).exists()

    def test_with_permissions(self, app, primary_collection, submission_provider, collection_with_provider, collection_without_provider, user_one, user_two, submission_two, subject_one, url, payload):
        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 1
        assert res.status_code == 200

        res = app.post_json_api(
            url,
            payload(guid=submission_two._id, status='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth)
        assert res.status_code == 201

        submission_three = self.submission_class(creator=user_two)  # user_one does not have referent perm

        res = app.post_json_api(
            url,
            payload(guid=submission_three._id, status='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth)
        assert res.status_code == 201

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 3
        assert res.status_code == 200

        assert not (collection_with_provider.guid_links.all() | collection_without_provider.guid_links.all()).filter(_id__in=[submission_two._id, submission_three._id]).exists()
        assert primary_collection.guid_links.filter(_id__in=[submission_two._id, submission_three._id]).count() == 2

    def test_choice_restrictions(self, app, primary_collection, submission_provider, user_one, submission_two, subject_one, url, payload):
        primary_collection.status_choices = ['one', 'two', 'three']
        primary_collection.collected_type_choices = ['asdf', 'fdsa']
        primary_collection.save()

        # Needs collected_type
        res = app.post_json_api(
            url,
            payload(guid=submission_two._id, status='one', subjects=[[subject_one._id]]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'not an acceptable "type"' in res.json['errors'][0]['detail']

        # Needs status
        res = app.post_json_api(
            url,
            payload(guid=submission_two._id, collected_type='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'not an acceptable "status"' in res.json['errors'][0]['detail']

        # Invalid status
        res = app.post_json_api(
            url,
            payload(guid=submission_two._id, collected_type='asdf', status='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'not an acceptable "status"' in res.json['errors'][0]['detail']

        # Invalid collected_type
        res = app.post_json_api(
            url,
            payload(guid=submission_two._id, collected_type='one', status='one', subjects=[[subject_one._id]]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'not an acceptable "type"' in res.json['errors'][0]['detail']

        # Valid
        res = app.post_json_api(
            url,
            payload(guid=submission_two._id, collected_type='asdf', status='two', subjects=[[subject_one._id]]),
            auth=user_one.auth)
        assert res.status_code == 201

    def test_filters(self, app, submission_provider, collection_with_provider, collection_without_provider, user_one, user_two, submission_one, submission_two, subject_one, url, payload):
        res = app.get('{}?filter[id]={}'.format(url, submission_one._id), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        res = app.get('{}?filter[id]={}'.format(url, submission_two._id), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0
        res = app.get('{}?filter[status]=fdsa'.format(url), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        res = app.get('{}?filter[collected_type]=asdf'.format(url), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

        # Sanity
        res = app.get('{}?filter[subjects]={}'.format(url, subject_one._id), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

        # Add one with a subject to filter for it
        res = app.post_json_api(
            url,
            payload(guid=submission_two._id, collected_type='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth)
        assert res.status_code == 201

        res = app.get('{}?filter[subjects]={}'.format(url, subject_one._id), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        res = app.get('{}?filter[collected_type]=asdf'.format(url), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1

@pytest.mark.django_db
class ProviderLicensesViewTestBaseMixin(ProviderMixinBase):

    @pytest.fixture()
    def provider(self):
        return self.provider_class()

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def licenses(self):
        return NodeLicense.objects.all()

    @pytest.fixture()
    def license_one(self, licenses):
        return licenses[0]

    @pytest.fixture()
    def license_two(self, licenses):
        return licenses[1]

    @pytest.fixture()
    def license_three(self, licenses):
        return licenses[2]

    def test_provider_has_no_acceptable_licenses_and_no_default(self, app, provider, licenses, url, license_one):
        provider.licenses_acceptable.clear()
        provider.default_license = None
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == len(licenses)

        # test filter on name
        res = app.get('{}?filter[name]={}'.format(url, license_one.name))
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == license_one._id

    def test_provider_has_a_default_license_but_no_acceptable_licenses(self, app, provider, licenses, license_two, url):
        provider.licenses_acceptable.clear()
        provider.default_license = license_two
        provider.save()
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == len(licenses)
        assert license_two._id in [item['id'] for item in res.json['data']]

        # test filter on default_license name
        res = app.get('{}?filter[name]={}'.format(url, license_two.name))
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == license_two._id

    def test_provider_has_acceptable_licenses_but_no_default(self, app, provider, licenses, license_one, license_two, license_three, url):
        provider.licenses_acceptable.add(license_one, license_two)
        provider.default_license = None
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        license_ids = [item['id'] for item in res.json['data']]
        assert license_one._id in license_ids
        assert license_two._id in license_ids
        assert license_three._id not in license_ids

    def test_provider_has_both_acceptable_and_default_licenses(self, app, provider, licenses, license_one, license_two, license_three, url):
        provider.licenses_acceptable.add(license_one, license_three)
        provider.default_license = license_three
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        license_ids = [item['id'] for item in res.json['data']]
        assert license_one._id in license_ids
        assert license_three._id in license_ids
        assert license_two._id not in license_ids
