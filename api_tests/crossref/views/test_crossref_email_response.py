import mock
import pytest

from osf_tests import factories
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestCrossRefEmailResponse:

    @pytest.fixture()
    def preprint(self):
        return factories.PreprintFactory()

    @pytest.fixture()
    def error_xml(self, preprint):
        return """
        <?xml version="1.0" encoding="UTF-8"?>
        <doi_batch_diagnostic status="completed" sp="cs3.crossref.org">
           <submission_id>1390675109</submission_id>
           <batch_id>{}</batch_id>
           <record_diagnostic status="Failure">
              <doi />
              <msg></msg>
           </record_diagnostic>
           <batch_data>
              <record_count>1</record_count>
              <success_count>0</success_count>
              <warning_count>0</warning_count>
              <failure_count>1</failure_count>
           </batch_data>
        </doi_batch_diagnostic>
        """.format(preprint._id)

    @pytest.fixture()
    def success_xml(self, preprint):
        return """
            <?xml version="1.0" encoding="UTF-8"?>
            <doi_batch_diagnostic status="completed" sp="cs3.crossref.org">
               <submission_id>1390675475</submission_id>
               <batch_id>{}</batch_id>
               <record_diagnostic status="Success">
                  <doi>10.31219/FK2OSF.IO/{}</doi>
                  <msg>Successfully added</msg>
               </record_diagnostic>
               <batch_data>
                  <record_count>1</record_count>
                  <success_count>1</success_count>
                  <warning_count>0</warning_count>
                  <failure_count>0</failure_count>
               </batch_data>
            </doi_batch_diagnostic>
        """.format(preprint._id, preprint._id)

    def mailgun_response(self, response):
        return {
            'From': ['CrossRef <admin@crossref.org>'],
            'To': ['test@test.osf.io'],
            'subject': ['CrossRef submission ID: 1390671938'],
            'from': ['CrossRef <test-admin@crossref.org>'],
            'Date': ['Fri, 27 Apr 2018 11:38:00 -0400 (EDT)'],
            'body-plain': [response.strip()],
            'Mime-Version': ['1.0'],
            'timestamp': ['1524843565'],
            'recipient': ['test@test.osf.io'],
            'sender': ['test-admin@crossref.org'],
            'Content-Type': [u'text/plain; charset="UTF-8"'],
            'Subject': [u'CrossRef submission ID: 1390671938']
        }

    def test_error_response_removes_doi_sends_message(self, app, preprint, error_xml):
        mailgun_response = self.mailgun_response(error_xml)
        url = '/{}_/crossref/email/'.format(API_BASE).replace('/v2', '')

        assert preprint.get_identifier_value('doi')

        with mock.patch('framework.auth.views.mails.send_mail') as mock_send_mail:
            app.post(url, mailgun_response)

        assert mock_send_mail.called
        assert not preprint.get_identifier_value('doi')

    def test_success_response_does_nothing(self, app, preprint, success_xml):
        mailgun_response = self.mailgun_response(success_xml)
        url = '/{}_/crossref/email/'.format(API_BASE).replace('/v2', '')

        assert preprint.get_identifier_value('doi')

        with mock.patch('framework.auth.views.mails.send_mail') as mock_send_mail:
            app.post(url, mailgun_response)

        assert not mock_send_mail.called
        assert preprint.get_identifier_value('doi')
