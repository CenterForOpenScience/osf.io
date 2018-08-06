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
