import pytest

from osf_tests.factories import ChronosJournalFactory


@pytest.mark.django_db
class TestChronosJournalList:

    @pytest.fixture()
    def journals(self):
        return [ChronosJournalFactory(), ChronosJournalFactory(), ChronosJournalFactory()]

    @pytest.fixture()
    def journal_ids(self, journals):
        return [j.journal_id for j in journals]

    @pytest.fixture()
    def url(self):
        return '/_/chronos/journals/'

    @pytest.fixture()
    def res(self, app, journals, url):
        return app.get(url)

    @pytest.fixture()
    def data(self, res):
        return res.json['data']

    def test_journal_list(self, res, data, journal_ids):
        assert res.status_code == 200
        assert set(journal_ids) == set([datum['id'] for datum in data])


@pytest.mark.django_db
class TestChronosJournalListFilter:

    @pytest.fixture()
    def journal_one(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def journal_two(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def journal_one_filter_name_url(self, journal_one):
        return '/_/chronos/journals/?filter[name]={}'.format(journal_one.name)

    @pytest.fixture()
    def journal_one_filter_title_url(self, journal_one):
        return '/_/chronos/journals/?filter[title]={}'.format(journal_one.title)

    def test_journal_list_filter(self, app, journal_one, journal_two, journal_one_filter_name_url, journal_one_filter_title_url):
        res = app.get(journal_one_filter_name_url)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['name'] == journal_one.name

        res = app.get(journal_one_filter_title_url)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['title'] == journal_one.title
