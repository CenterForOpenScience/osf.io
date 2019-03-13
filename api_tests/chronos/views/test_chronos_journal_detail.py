import pytest

from osf_tests.factories import ChronosJournalFactory


@pytest.mark.django_db
class TestChronosJournalDetail:

    @pytest.fixture()
    def journal(self):
        return ChronosJournalFactory()

    @pytest.fixture()
    def url(self, journal):
        return '/_/chronos/journals/{}/'.format(journal.journal_id)

    @pytest.fixture()
    def res(self, app, url):
        return app.get(url)

    @pytest.fixture()
    def data(self, res):
        return res.json['data']

    def test_journal_detail(self, res, data, journal):
        assert res.status_code == 200
        assert data['type'] == 'chronos-journals'
        assert data['id'] == journal.journal_id
        assert data['attributes']['name'] == journal.name
