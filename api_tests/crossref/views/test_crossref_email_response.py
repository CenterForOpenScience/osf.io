import mock
import pytest
import hmac
import hashlib
import lxml.etree

from django.utils import timezone

from osf_tests import factories
from website import settings


@pytest.mark.django_db
class TestCrossRefEmailResponse:

    def make_mailgun_payload(self, crossref_response):
        mailgun_payload = {
            'From': ['CrossRef <admin@crossref.org>'],
            'To': ['test@test.osf.io'],
            'subject': ['CrossRef submission ID: 1390671938'],
            'from': ['CrossRef <test-admin@crossref.org>'],
            'Date': ['Fri, 27 Apr 2018 11:38:00 -0400 (EDT)'],
            'body-plain': [crossref_response.strip()],
            'Mime-Version': ['1.0'],
            'timestamp': '123',
            'recipient': ['test@test.osf.io'],
            'sender': ['test-admin@crossref.org'],
            'Content-Type': [u'text/plain; charset="UTF-8"'],
            'Subject': [u'CrossRef submission ID: 1390671938'],
            'token': 'secret'
        }

        # temporarily override MAILGUN_API_KEY
        settings.MAILGUN_API_KEY = 'notsosecret'
        data = {
            'X-Mailgun-Sscore': 0,
            'signature': hmac.new(
                key=settings.MAILGUN_API_KEY,
                msg='{}{}'.format(
                    mailgun_payload['timestamp'],
                    mailgun_payload['token']
                ),
                digestmod=hashlib.sha256,
            ).hexdigest(),
        }
        data.update(mailgun_payload)
        data = {
            key: value
            for key, value in data.iteritems()
            if value is not None
        }
        return data

    @pytest.fixture()
    def preprint(self):
        return factories.PreprintFactory(set_doi=False)

    @pytest.fixture()
    def error_xml(self, preprint):
        return """
        <?xml version="1.0" encoding="UTF-8"?>
        <doi_batch_diagnostic status="completed" sp="cs3.crossref.org">
           <submission_id>1390675109</submission_id>
           <batch_id>{}</batch_id>
           <record_diagnostic status="Failure">
              <doi />
              <msg>Error: cvc-complex-type.2.4.a: Invalid content was found starting with element 'program'</msg>
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

    @pytest.fixture()
    def update_success_xml(self, preprint):
        return """
        <?xml version="1.0" encoding="UTF-8"?>
        <doi_batch_diagnostic status="completed" sp="cs3.crossref.org">
            <submission_id>1390757455</submission_id>
            <batch_id>{}</batch_id>
            <record_diagnostic status="Success">
                <doi>10.31219/FK2osf.io/{}</doi>
                <msg>Successfully updated</msg>
            </record_diagnostic>
            <batch_data>
                <record_count>1</record_count>
                <success_count>1</success_count>
                <warning_count>0</warning_count>
                <failure_count>0</failure_count>
            </batch_data>
        </doi_batch_diagnostic>
        """.format(preprint._id, preprint._id)

    def build_batch_success_xml(self, preprint_list):
        preprint_count = len(preprint_list)
        base_xml_string = """
        <?xml version="1.0" encoding="UTF-8"?>
        <doi_batch_diagnostic status="completed" sp="cs3.crossref.org">
            <submission_id>1390758391</submission_id>
            <batch_id>1528233706</batch_id>
            <batch_data>
                <record_count>{}</record_count>
                <success_count>{}</success_count>
                <warning_count>0</warning_count>
                <failure_count>0</failure_count>
            </batch_data>
        </doi_batch_diagnostic>
        """.format(preprint_count, preprint_count)
        base_xml = lxml.etree.fromstring(base_xml_string.strip())
        provider_prefix = preprint_list[0].provider.doi_prefix
        for preprint in preprint_list:
            record_diagnostic = lxml.etree.Element('record_diagnostic')
            record_diagnostic.attrib['status'] = 'Success'
            doi = lxml.etree.Element('doi')
            doi.text = settings.DOI_FORMAT.format(prefix=provider_prefix, guid=preprint._id)
            msg = lxml.etree.Element('msg')
            msg.text = 'Successfully added'
            record_diagnostic.append(doi)
            record_diagnostic.append(msg)
            base_xml.append(record_diagnostic)

        return lxml.etree.tostring(base_xml, pretty_print=False)

    @pytest.fixture()
    def url(self):
        return '/_/crossref/email/'

    def test_wrong_request_context_raises_permission_error(self, app, url, error_xml):
        mailgun_response = self.make_mailgun_payload(error_xml)
        mailgun_response.pop('signature')
        response = app.post(url, mailgun_response, expect_errors=True)

        assert response.status_code == 400

    def test_error_response_sends_message_does_not_set_doi(self, app, url, preprint, error_xml):
        assert not preprint.get_identifier_value('doi')

        with mock.patch('framework.auth.views.mails.send_mail') as mock_send_mail:
            context_data = self.make_mailgun_payload(crossref_response=error_xml)
            app.post(url, context_data)
        assert mock_send_mail.called
        assert not preprint.get_identifier_value('doi')

    def test_success_response_sets_doi(self, app, url, preprint, success_xml):
        assert not preprint.get_identifier_value('doi')

        with mock.patch('framework.auth.views.mails.send_mail') as mock_send_mail:
            context_data = self.make_mailgun_payload(crossref_response=success_xml)
            app.post(url, context_data)

        preprint.reload()
        assert not mock_send_mail.called
        assert preprint.get_identifier_value('doi')
        assert preprint.preprint_doi_created

    def test_update_success_response(self, app, preprint, url, update_success_xml):
        initial_value = 'TempDOIValue'
        preprint.set_identifier_value(category='doi', value=initial_value)
        update_xml = self.update_success_xml(preprint)

        with mock.patch('framework.auth.views.mails.send_mail') as mock_send_mail:
            context_data = self.make_mailgun_payload(crossref_response=update_xml)
            app.post(url, context_data)

        assert not mock_send_mail.called
        assert preprint.get_identifier_value(category='doi') != initial_value

    def test_update_success_does_not_set_prerprint_doi_created(self, app, preprint, url, update_success_xml):
        preprint.set_identifier_value(category='doi', value='test')
        preprint.preprint_doi_created = timezone.now()
        preprint.save()
        update_xml = self.update_success_xml(preprint)

        pre_created = preprint.preprint_doi_created
        with mock.patch('framework.auth.views.mails.send_mail'):
            context_data = self.make_mailgun_payload(crossref_response=update_xml)
            app.post(url, context_data)

        assert preprint.preprint_doi_created == pre_created

    def test_success_batch_response(self, app, url):
        provider = factories.PreprintProviderFactory()
        provider.doi_prefix = '10.123yeah'
        provider.save()
        preprint_list = [factories.PreprintFactory(set_doi=False, provider=provider) for _ in range(5)]

        xml_response = self.build_batch_success_xml(preprint_list)
        context_data = self.make_mailgun_payload(xml_response)
        app.post(url, context_data)

        for preprint in preprint_list:
            assert preprint.get_identifier_value('doi') == settings.DOI_FORMAT.format(prefix=provider.doi_prefix, guid=preprint._id)

    def test_confirmation_marks_legacy_doi_as_deleted(self, app, url, preprint, update_success_xml):
        legacy_value = 'IAmALegacyDOI'
        preprint.set_identifier_value(category='legacy_doi', value=legacy_value)
        update_xml = self.update_success_xml(preprint)

        with mock.patch('framework.auth.views.mails.send_mail') as mock_send_mail:
            context_data = self.make_mailgun_payload(crossref_response=update_xml)
            app.post(url, context_data)

        assert not mock_send_mail.called
        assert preprint.identifiers.get(category='legacy_doi').deleted
