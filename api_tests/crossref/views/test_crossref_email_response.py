import pytest
import hmac
import hashlib
import lxml.etree

from django.utils import timezone

from osf.models import NotificationTypeEnum
from osf_tests import factories
from tests.utils import capture_notifications
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
            'Content-Type': ['text/plain; charset="UTF-8"'],
            'Subject': ['CrossRef submission ID: 1390671938'],
            'token': 'secret'
        }

        # temporarily override MAILGUN_API_KEY
        settings.MAILGUN_API_KEY = 'notsosecret'
        data = {
            'X-Mailgun-Sscore': 0,
            'signature': hmac.new(
                key=settings.MAILGUN_API_KEY.encode(),
                msg='{}{}'.format(
                    mailgun_payload['timestamp'],
                    mailgun_payload['token']
                ).encode(),
                digestmod=hashlib.sha256,
            ).hexdigest(),
        }
        data.update(mailgun_payload)
        data = {
            key: value
            for key, value in data.items()
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
        base_xml = lxml.etree.fromstring(base_xml_string.strip().encode())
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

        context_data = self.make_mailgun_payload(crossref_response=error_xml)
        with capture_notifications() as notifications:
            app.post(url, context_data)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.DESK_CROSSREF_ERROR
        assert not preprint.get_identifier_value('doi')

    def test_success_response_sets_doi(self, app, url, preprint, success_xml):
        assert not preprint.get_identifier_value('doi')

        context_data = self.make_mailgun_payload(crossref_response=success_xml)
        app.post(url, context_data)

        preprint.reload()
        assert preprint.get_identifier_value('doi')
        assert preprint.preprint_doi_created

    def test_update_success_response(self, app, preprint, url):
        initial_value = 'TempDOIValue'
        preprint.set_identifier_value(category='doi', value=initial_value)
        update_xml = self.update_success_xml(preprint)

        context_data = self.make_mailgun_payload(crossref_response=update_xml)
        app.post(url, context_data)
        assert preprint.get_identifier_value(category='doi') != initial_value

    def test_update_success_does_not_set_preprint_doi_created(self, app, preprint, url):
        preprint.set_identifier_value(category='doi', value='test')
        preprint.preprint_doi_created = timezone.now()
        preprint.save()
        update_xml = self.update_success_xml(preprint)

        pre_created = preprint.preprint_doi_created
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

    def test_confirmation_marks_legacy_doi_as_deleted(self, app, url, preprint):
        legacy_value = 'IAmALegacyDOI'
        preprint.set_identifier_value(category='legacy_doi', value=legacy_value)
        update_xml = self.update_success_xml(preprint)

        context_data = self.make_mailgun_payload(crossref_response=update_xml)
        with capture_notifications(expect_none=True):
            app.post(url, context_data)

        assert preprint.identifiers.get(category='legacy_doi').deleted

    def test_unversioned_doi_confirmation_skips_identifier_update(self, app, url, preprint):
        versioned_doi = settings.DOI_FORMAT.format(
            prefix=preprint.provider.doi_prefix, guid=preprint._id
        )
        preprint.set_identifier_value(category='doi', value=versioned_doi)

        base_guid = preprint.get_guid()._id  # no _vN suffix
        unversioned_doi = settings.DOI_FORMAT.format(
            prefix=preprint.provider.doi_prefix, guid=base_guid
        )
        dual_confirmation_xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <doi_batch_diagnostic status="completed" sp="cs3.crossref.org">
               <submission_id>1390675999</submission_id>
               <batch_id>{batch_id}</batch_id>
               <record_diagnostic status="Success">
                  <doi>{versioned_doi}</doi>
                  <msg>Successfully updated</msg>
               </record_diagnostic>
               <record_diagnostic status="Success">
                  <doi>{unversioned_doi}</doi>
                  <msg>Successfully added</msg>
               </record_diagnostic>
               <batch_data>
                  <record_count>2</record_count>
                  <success_count>2</success_count>
                  <warning_count>0</warning_count>
                  <failure_count>0</failure_count>
               </batch_data>
            </doi_batch_diagnostic>
        """.format(
            batch_id=preprint._id,
            versioned_doi=versioned_doi,
            unversioned_doi=unversioned_doi,
        )

        context_data = self.make_mailgun_payload(crossref_response=dual_confirmation_xml)
        with capture_notifications(expect_none=True):
            app.post(url, context_data)

        preprint.reload()
        assert preprint.get_identifier_value('doi') == versioned_doi
        assert preprint.get_identifier_value('doi_unversioned') == unversioned_doi

    def test_unversioned_doi_confirmation_update_does_not_store_doi_unversioned(self, app, url, preprint):
        versioned_doi = settings.DOI_FORMAT.format(
            prefix=preprint.provider.doi_prefix, guid=preprint._id
        )
        preprint.set_identifier_value(category='doi', value=versioned_doi)

        base_guid = preprint.get_guid()._id
        unversioned_doi = settings.DOI_FORMAT.format(
            prefix=preprint.provider.doi_prefix, guid=base_guid
        )
        update_confirmation_xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <doi_batch_diagnostic status="completed" sp="cs3.crossref.org">
               <submission_id>1390676000</submission_id>
               <batch_id>{batch_id}</batch_id>
               <record_diagnostic status="Success">
                  <doi>{versioned_doi}</doi>
                  <msg>Successfully updated</msg>
               </record_diagnostic>
               <record_diagnostic status="Success">
                  <doi>{unversioned_doi}</doi>
                  <msg>Successfully updated</msg>
               </record_diagnostic>
               <batch_data>
                  <record_count>2</record_count>
                  <success_count>2</success_count>
                  <warning_count>0</warning_count>
                  <failure_count>0</failure_count>
               </batch_data>
            </doi_batch_diagnostic>
        """.format(
            batch_id=preprint._id,
            versioned_doi=versioned_doi,
            unversioned_doi=unversioned_doi,
        )

        context_data = self.make_mailgun_payload(crossref_response=update_confirmation_xml)
        with capture_notifications(expect_none=True):
            app.post(url, context_data)

        preprint.reload()
        assert preprint.get_identifier_value('doi') == versioned_doi
        assert preprint.get_identifier_value('doi_unversioned') == unversioned_doi

    def _post_records(self, app, url, preprint, records, expect_none=True):
        body = ''.join(
            f'<record_diagnostic status="{status}"><doi>{doi}</doi><msg>{msg}</msg></record_diagnostic>'
            for doi, status, msg in records
        )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<doi_batch_diagnostic status="completed" sp="cs3.crossref.org">'
            f'<submission_id>1</submission_id><batch_id>{preprint._id}</batch_id>{body}'
            f'<batch_data><record_count>{len(records)}</record_count></batch_data>'
            '</doi_batch_diagnostic>'
        )
        data = self.make_mailgun_payload(crossref_response=xml)
        if expect_none:
            with capture_notifications(expect_none=True):
                app.post(url, data)
        else:
            app.post(url, data)

    def _dois(self, preprint):
        prefix = preprint.provider.doi_prefix
        return (
            settings.DOI_FORMAT.format(prefix=prefix, guid=preprint._id),
            settings.DOI_FORMAT.format(prefix=prefix, guid=preprint.get_guid()._id),
        )

    def test_success_clears_in_flight_marker(self, app, url, preprint):
        versioned, unversioned = self._dois(preprint)
        preprint.doi_resync_queued_at = timezone.now()
        preprint.save()
        self._post_records(app, url, preprint, [
            (versioned, 'Success', 'Successfully updated'),
            (unversioned, 'Success', 'Successfully updated'),
        ])
        preprint.reload()
        assert preprint.doi_resync_queued_at is None

    def test_unversioned_success_alone_clears_in_flight_marker(self, app, url, preprint):
        _, unversioned = self._dois(preprint)
        preprint.doi_resync_queued_at = timezone.now()
        preprint.save()
        self._post_records(app, url, preprint, [(unversioned, 'Success', 'Successfully updated')])
        preprint.reload()
        assert preprint.doi_resync_queued_at is None
        assert preprint.get_identifier_value('doi_unversioned') == unversioned

    def test_less_or_equal_failure_clears_marker_and_stores_unversioned(self, app, url, preprint):
        versioned, unversioned = self._dois(preprint)
        preprint.doi_resync_queued_at = timezone.now()
        preprint.save()
        msg = 'Record not processed because submitted version number is less or equal to previously submitted version'
        self._post_records(app, url, preprint, [
            (versioned, 'Failure', msg),
            (unversioned, 'Failure', msg),
        ])
        preprint.reload()
        assert preprint.doi_resync_queued_at is None
        assert preprint.get_identifier_value('doi_unversioned') == unversioned

    def test_less_or_equal_failure_on_v1_stores_versioned_doi(self, app, url, preprint):
        # Crossref already has the v1 DOI; without storing it the preprint would be resubmitted every tick.
        from osf.management.commands.resync_preprint_dois_v1 import get_preprints_needing_v1_doi
        versioned, _ = self._dois(preprint)
        preprint.doi_resync_queued_at = timezone.now()
        preprint.save()
        msg = 'Record not processed because submitted version number is less or equal to previously submitted version'
        self._post_records(app, url, preprint, [(versioned, 'Failure', msg)])
        preprint.reload()
        assert preprint.doi_resync_queued_at is None
        assert preprint.get_identifier_value('doi') == versioned
        assert not get_preprints_needing_v1_doi().filter(id=preprint.id).exists()

    def test_unexpected_failure_keeps_marker_as_cooldown(self, app, url, preprint):
        versioned, _ = self._dois(preprint)
        preprint.doi_resync_queued_at = timezone.now()
        preprint.save()
        self._post_records(app, url, preprint, [(versioned, 'Failure', 'Something unexpected')], expect_none=False)
        preprint.reload()
        assert preprint.doi_resync_queued_at is not None

    def test_later_version_failure_keeps_v1_marker(self, app, url, preprint):
        preprint.doi_resync_queued_at = timezone.now()
        preprint.save()
        v2_doi = settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=f'{preprint.get_guid()._id}_v2')
        msg = 'Record not processed because submitted version number is less or equal to previously submitted version'
        self._post_records(app, url, preprint, [(v2_doi, 'Failure', msg)])
        preprint.reload()
        assert preprint.doi_resync_queued_at is not None

    def test_relation_target_failure_keeps_marker(self, app, url, preprint):
        from unittest import mock
        versioned, _ = self._dois(preprint)
        preprint.doi_resync_queued_at = timezone.now()
        preprint.save()
        with mock.patch('api.crossref.views.mint_doi_on_crossref_fail') as mock_mint:
            self._post_records(app, url, preprint, [(versioned, 'Failure', 'Relation target DOI does not exist')], expect_none=False)
        mock_mint.apply_async.assert_called_once()
        preprint.reload()
        assert preprint.doi_resync_queued_at is not None
