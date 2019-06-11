# encoding: utf-8
import os
import mock
import pytest
import json
from datetime import timedelta
import responses
HERE = os.path.dirname(os.path.abspath(__file__))


from osf_tests.factories import PreprintFactory
from website import settings, mails

from scripts.periodic.check_crossref_dois import check_crossref_dois, report_stuck_dois


@pytest.mark.django_db
class TestCheckCrossrefDOIs:

    @pytest.fixture()
    def stuck_preprint(self):
        preprint = PreprintFactory(set_doi=False)
        published_date = preprint.date_published - timedelta(days=settings.DAYS_CROSSREF_DOIS_MUST_BE_STUCK_BEFORE_EMAIL + 1)
        preprint.date_published = published_date
        # match guid to the fixture crossref_works_response.json
        guid = preprint.guids.first()
        provider = preprint.provider
        provider.doi_prefix = '10.31236'
        provider.save()
        guid._id = 'guid0'
        guid.save()

        preprint.save()
        return preprint

    @pytest.fixture()
    def crossref_response(self):
        with open(os.path.join(HERE, 'fixtures/crossref_works_response.json'), 'rb') as fp:
            return json.loads(fp.read())

    @responses.activate
    def test_check_crossref_dois(self, crossref_response, stuck_preprint):
        doi = settings.DOI_FORMAT.format(prefix=stuck_preprint.provider.doi_prefix, guid=stuck_preprint.guids.first()._id)
        responses.add(
            responses.Response(
                responses.GET,
                url='{}/works?filter=doi:{}'.format(settings.CROSSREF_JSON_API_URL, doi),
                json=crossref_response,
                status=200
            )
        )

        check_crossref_dois(dry_run=False)

        assert stuck_preprint.identifiers.count() == 1
        assert stuck_preprint.identifiers.first().value == doi

    @mock.patch('website.mails.send_mail')
    def test_report_stuck_dois(self, mock_email, stuck_preprint):
        report_stuck_dois(dry_run=False)
        guid = stuck_preprint.guids.first()._id
        email_content = 'DOIs for the following preprints have been pending at least {} days: {}'.format(settings.DAYS_CROSSREF_DOIS_MUST_BE_STUCK_BEFORE_EMAIL, guid)

        mock_email.assert_called_with(email_content=email_content,
                                      mail=mails.CROSSREF_DOIS_PENDING,
                                      pending_doi_count=1,
                                      to_addr=settings.OSF_SUPPORT_EMAIL)