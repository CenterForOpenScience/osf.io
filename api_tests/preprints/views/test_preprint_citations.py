from api.base.settings.defaults import API_BASE
from api.citations.utils import render_citation
from django.utils import timezone
from osf_tests.factories import AuthUserFactory, PreprintFactory
from tests.base import ApiTestCase
from osf.utils.permissions import WRITE
from osf.utils.workflows import DefaultStates


class PreprintCitationsMixin:

    def setUp(self):
        super().setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            creator=self.admin_contributor)
        self.unpublished_preprint = PreprintFactory(
            creator=self.admin_contributor, is_published=False)

    def test_unauthenticated_can_view_published_preprint_citations(self):
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200

    def test_unauthenticated_cannot_view_unpublished_preprint_citations(self):
        res = self.app.get(self.unpublished_preprint_url, expect_errors=True)
        assert res.status_code == 401

    def test_preprint_citations_are_read_only(self):
        post_res = self.app.post_json_api(
            self.published_preprint_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert post_res.status_code == 405
        put_res = self.app.put_json_api(
            self.published_preprint_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert put_res.status_code == 405
        delete_res = self.app.delete_json_api(
            self.published_preprint_url,
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert delete_res.status_code == 405


class TestPreprintCitations(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super().setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.unpublished_preprint._id)
        self.other_contrib = AuthUserFactory()

    def test_citation_publisher_is_preprint_provider(self):
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['publisher'] == \
            self.published_preprint.provider.name

    def test_citation_url_is_preprint_url_not_project(self):
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        assert res.json['data']['links']['self'] == \
            self.published_preprint.display_absolute_url

class TestPreprintCitationsPermissions(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super().setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.unpublished_preprint._id)
        self.other_contrib = AuthUserFactory()

    def test_unpublished_preprint_citations(self):
        # Unauthenticated
        res = self.app.get(self.unpublished_preprint_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = self.app.get(self.unpublished_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        self.unpublished_preprint.add_contributor(self.other_contrib, WRITE, save=True)
        res = self.app.get(self.unpublished_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state, not because of published flag
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.unpublished_preprint_url, auth=self.admin_contributor.auth)
        assert res.status_code == 200

    def test_private_preprint_citations(self):
        self.published_preprint.is_public = False
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, WRITE, save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth)
        # Really because preprint is in initial machine state
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert res.status_code == 200

    def test_deleted_preprint_citations(self):
        self.published_preprint.deleted = timezone.now()
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert res.status_code == 404

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert res.status_code == 404

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, WRITE, save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert res.status_code == 404

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth, expect_errors=True)
        assert res.status_code == 404

    def test_abandoned_preprint_citations(self):
        self.published_preprint.machine_state = DefaultStates.INITIAL.value
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, WRITE, save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert res.status_code == 200


class TestPreprintCitationContent(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super().setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.unpublished_preprint._id)

    def test_citation_contains_correct_date(self):
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        expected_date = self.published_preprint.date_published.strftime('%Y, %B %-d')
        assert expected_date in res.json['data']['attributes']['citation']

    def test_citation_no_date(self):
        self.published_preprint.date_published = None
        self.published_preprint.save()

        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        expected_date = 'n.d.'
        assert expected_date in res.json['data']['attributes']['citation']


class TestPreprintCitationsContentPermissions(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super().setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.unpublished_preprint._id)
        self.other_contrib = AuthUserFactory()

    def test_unpublished_preprint_citations(self):
        # Unauthenticated
        res = self.app.get(self.unpublished_preprint_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = self.app.get(self.unpublished_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        self.unpublished_preprint.add_contributor(self.other_contrib, WRITE, save=True)
        res = self.app.get(self.unpublished_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state, not because of published flag
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.unpublished_preprint_url, auth=self.admin_contributor.auth)
        assert res.status_code == 200

    def test_private_preprint_citations(self):
        self.published_preprint.is_public = False
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, WRITE, save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth)
        # Really because preprint is in initial machine state
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert res.status_code == 200

    def test_deleted_preprint_citations(self):
        self.published_preprint.deleted = timezone.now()
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert res.status_code == 404

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert res.status_code == 404

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, WRITE, save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert res.status_code == 404

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth, expect_errors=True)
        assert res.status_code == 404

    def test_abandoned_preprint_citations(self):
        self.published_preprint.machine_state = DefaultStates.INITIAL.value
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert res.status_code == 401

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, WRITE, save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert res.status_code == 200


class TestPreprintCitationContentMLA(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            creator=self.admin_contributor)
        self.published_preprint.title = 'My Preprint'
        self.published_preprint.save()

        self.admin_contributor.given_name = 'Grapes'
        self.admin_contributor.middle_names = ' Coffee Beans '
        self.admin_contributor.family_name = 'McGee'
        self.admin_contributor.save()
        self.published_preprint_url = '/{}preprints/{}/citation/modern-language-association/'.format(
            API_BASE, self.published_preprint._id)

        self.second_contrib = AuthUserFactory()
        self.second_contrib.given_name = 'Darla'
        self.second_contrib.middle_names = 'Texas Toast'
        self.second_contrib.family_name = 'Jenkins'
        self.second_contrib.suffix = 'Junior'
        self.second_contrib.save()

        self.third_contrib = AuthUserFactory()
        self.third_contrib.given_name = 'Lilith'
        self.third_contrib.middle_names = 'Radar'
        self.third_contrib.family_name = 'Schematics'
        self.third_contrib.save()

    def test_not_published(self):
        self.published_preprint.date_published = None
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == f'McGee, Grapes C. B. “{self.published_preprint.title}.” {self.published_preprint.provider.name}, n.d. Web.'

    def test_one_author(self):
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == render_citation(self.published_preprint, 'modern-language-association')

        # test_suffix
        self.admin_contributor.suffix = 'Junior'
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == render_citation(self.published_preprint, 'modern-language-association')

        # test_no_middle_names
        self.admin_contributor.suffix = ''
        self.admin_contributor.middle_names = ''
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == render_citation(self.published_preprint, 'modern-language-association')

    def test_citation_no_repeated_periods(self):
        self.published_preprint.title = 'A Study of Coffee.'
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == render_citation(self.published_preprint, 'modern-language-association')

    def test_citation_osf_provider(self):
        self.published_preprint.title = 'A Study of Coffee.'
        self.published_preprint.save()
        self.published_preprint.provider.name = 'Open Science Framework'
        self.published_preprint.provider.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == render_citation(self.published_preprint, 'modern-language-association')

    def test_two_authors(self):
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == render_citation(self.published_preprint, 'modern-language-association')

    def test_three_authors(self):
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.add_contributor(self.third_contrib)
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == render_citation(self.published_preprint, 'modern-language-association')

        # first name suffix
        self.admin_contributor.suffix = 'Jr.'
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == render_citation(self.published_preprint, 'modern-language-association')


class TestPreprintCitationContentAPA(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            title='A Study of Coffee',
            creator=self.admin_contributor
        )
        self.published_preprint.save()

        self.admin_contributor.given_name = 'Grapes'
        self.admin_contributor.middle_names = ' Coffee Beans '
        self.admin_contributor.family_name = 'McGee'
        self.admin_contributor.save()

        self.second_contrib = AuthUserFactory()
        self.second_contrib.given_name = 'Darla'
        self.second_contrib.middle_names = 'Texas Toast'
        self.second_contrib.family_name = 'Jenkins'
        self.second_contrib.suffix = 'Junior'
        self.second_contrib.save()

        self.third_contrib = AuthUserFactory()
        self.third_contrib.given_name = 'Lilith'
        self.third_contrib.middle_names = 'Radar'
        self.third_contrib.family_name = 'Schematics'
        self.third_contrib.save()

        self.published_preprint_url = f'/{API_BASE}preprints/{self.published_preprint._id}/citation/apa/'

    def test_not_published(self):
        self.published_preprint.date_published = None
        self.published_preprint.save()
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == (f'McGee, G. C. B., & Jenkins, D. T. T., Junior. (n.d.). {self.published_preprint.title}. '
                            f'{'https://doi.org/' + self.published_preprint.get_identifier('doi').value}')

    def test_one_author(self):
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published.strftime('%Y, %B %-d')
        assert citation == (f'McGee, G. C. B. ({date}). {self.published_preprint.title}. '
                            f'{'https://doi.org/' + self.published_preprint.get_identifier('doi').value}')

        # test_suffix
        self.admin_contributor.suffix = 'Junior'
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published.strftime('%Y, %B %-d')
        assert citation == (f'McGee, G. C. B., Junior. ({date}). {self.published_preprint.title}. '
                            f'{'https://doi.org/' + self.published_preprint.get_identifier('doi').value}')

        # test_no_middle_names
        self.admin_contributor.suffix = ''
        self.admin_contributor.middle_names = ''
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published.strftime('%Y, %B %-d')
        assert citation == (f'McGee, G. ({date}). {self.published_preprint.title}.'
                            f' {'https://doi.org/' + self.published_preprint.get_identifier('doi').value}')

    def test_two_authors(self):
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published.strftime('%Y, %B %-d')
        assert citation == (f"McGee, G. C. B., & Jenkins, D. T. T., Junior. ({date}). {self.published_preprint.title}. "
                            f"{'https://doi.org/' + self.published_preprint.get_identifier('doi').value}")

    def test_three_authors_and_title_with_period(self):
        self.published_preprint.title = 'This Title Ends in a Period.'
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.add_contributor(self.third_contrib)
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published.strftime('%Y, %B %-d')
        assert citation == (f'McGee, G. C. B., Jenkins, D. T. T., Junior, & Schematics, L. R. ({date}).'
                            f' This Title Ends in a Period. '
                            f'{"https://doi.org/" + self.published_preprint.get_identifier("doi").value}')

    def test_seven_authors(self):
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.add_contributor(self.third_contrib)
        for i in range(1, 5):
            new_user = AuthUserFactory()
            new_user.given_name = 'James'
            new_user.family_name = f'Taylor{i}'
            new_user.save()
            self.published_preprint.add_contributor(new_user)
        self.published_preprint.save()

        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published.strftime('%Y, %B %-d')
        assert citation == (f'McGee, G. C. B., Jenkins, D. T. T., Junior, Schematics, L. R., Taylor1, J., Taylor2, J.,'
                            f' Taylor3, J., & Taylor4, J. ({date}). {self.published_preprint.title}.'
                            f' {'https://doi.org/' + self.published_preprint.get_identifier("doi").value}')

    def test_eight_authors(self):
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.add_contributor(self.third_contrib)
        for i in range(1, 6):
            new_user = AuthUserFactory()
            new_user.given_name = 'James'
            new_user.family_name = f'Taylor{i}'
            new_user.save()
            self.published_preprint.add_contributor(new_user)
        self.published_preprint.save()

        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published.strftime('%Y, %B %-d')
        assert citation == (f"McGee, G. C. B., Jenkins, D. T. T., Junior, Schematics, L. R., Taylor1, "
                            f"J., Taylor2, J., Taylor3, J., … Taylor5, J. ({date}). {self.published_preprint.title}."
                            f" {'https://doi.org/' + self.published_preprint.get_identifier("doi").value}")


class TestPreprintCitationContentChicago(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            title='A Study of Coffee',
            creator=self.admin_contributor
        )
        self.published_preprint.save()

        self.admin_contributor.given_name = 'Grapes'
        self.admin_contributor.middle_names = ' Coffee Beans '
        self.admin_contributor.family_name = 'McGee'
        self.admin_contributor.save()
        self.published_preprint_url = f'/{API_BASE}preprints/{self.published_preprint._id}/citation/chicago-author-date/'

        self.second_contrib = AuthUserFactory()
        self.second_contrib.given_name = 'Darla'
        self.second_contrib.middle_names = 'Texas Toast'
        self.second_contrib.family_name = 'Jenkins'
        self.second_contrib.suffix = 'Junior'
        self.second_contrib.save()

        self.third_contrib = AuthUserFactory()
        self.third_contrib.given_name = 'Lilith'
        self.third_contrib.middle_names = 'Radar'
        self.third_contrib.family_name = 'Schematics'
        self.third_contrib.save()

    def test_not_published(self):
        self.published_preprint.date_published = None
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        assert citation == (f'McGee, Grapes C. B. n.d. “{self.published_preprint.title}.” '
                            f'{self.published_preprint.provider.name}.'
                            f' {'doi:' + self.published_preprint.get_identifier("doi").value}.')

    def test_one_author(self):
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published
        assert citation == (f'McGee, Grapes C. B. {date.strftime('%Y')}. “{self.published_preprint.title}.” '
                            f'{self.published_preprint.provider.name}. {date.strftime('%B %-d')}.'
                            f' {'doi:' + self.published_preprint.get_identifier("doi").value}.')

    def test_suffix(self):

        self.admin_contributor.suffix = 'Junior'
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published
        assert citation == (f'McGee, Grapes C. B., Junior. {date.strftime('%Y')}. “{self.published_preprint.title}.”'
                            f' {self.published_preprint.provider.name}. {date.strftime('%B %-d')}.'
                            f' {'doi:' + self.published_preprint.get_identifier("doi").value}.')

    def test_no_middle_names(self):
        self.admin_contributor.suffix = ''
        self.admin_contributor.middle_names = ''
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published
        assert citation == (f'McGee, Grapes. {date.strftime('%Y')}. “{self.published_preprint.title}.”'
                            f' {self.published_preprint.provider.name}. {date.strftime('%B %-d')}.'
                            f' {'doi:' + self.published_preprint.get_identifier("doi").value}.')

    def test_two_authors(self):
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published
        assert citation == (f'McGee, Grapes C. B., and Darla T. T. Jenkins, Junior. {date.strftime('%Y')}. '
                            f'“{self.published_preprint.title}.” {self.published_preprint.provider.name}.'
                            f' {date.strftime('%B %-d')}. {'doi:' + self.published_preprint.get_identifier("doi").value}.')

    def test_three_authors_and_title_with_period(self):
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.add_contributor(self.third_contrib)
        self.published_preprint.title = 'This Preprint ends in a Period.'
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published
        assert citation == (f'McGee, Grapes C. B., Darla T. T. Jenkins, Junior, and Lilith R. Schematics. '
                            f'{date.strftime('%Y')}. “This Preprint Ends in a Period.” '
                            f'{self.published_preprint.provider.name}. '
                            f'{date.strftime('%B %-d')}. {'doi:' + self.published_preprint.get_identifier("doi").value}.')

    def test_eleven_contributors(self):
        self.published_preprint.add_contributor(self.second_contrib)
        self.published_preprint.add_contributor(self.third_contrib)
        for i in range(1, 9):
            new_user = AuthUserFactory()
            new_user.given_name = 'James'
            new_user.family_name = f'Taylor{i}'
            new_user.save()
            self.published_preprint.add_contributor(new_user)
        self.published_preprint.save()
        res = self.app.get(self.published_preprint_url)
        assert res.status_code == 200
        citation = res.json['data']['attributes']['citation']
        date = self.published_preprint.date_published
        assert citation == (f'McGee, Grapes C. B., Darla T. T. Jenkins, Junior, Lilith R. Schematics, James Taylor1, '
                            f'James Taylor2, James Taylor3, James Taylor4, et al. {date.strftime('%Y')}.'
                            f' “{self.published_preprint.title}.” {self.published_preprint.provider.name}. '
                            f'{date.strftime('%B %-d')}. {'doi:' + self.published_preprint.get_identifier("doi").value}.')
