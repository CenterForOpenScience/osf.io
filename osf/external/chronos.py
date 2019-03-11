from __future__ import unicode_literals
import requests

from django.db import transaction

from api.files.serializers import get_file_download_link
from osf.models import ChronosJournal
from osf.models import ChronosSubmission
from osf.utils.workflows import ChronosSubmissionStatus, ReviewStates
from website.settings import (
    CHRONOS_USE_FAKE_FILE, CHRONOS_FAKE_FILE_URL,
    CHRONOS_API_KEY, CHRONOS_USERNAME, CHRONOS_PASSWORD, CHRONOS_HOST, VERIFY_CHRONOS_SSL_CERT
)


class ChronosSerializer(object):

    @classmethod
    def serialize_manuscript(cls, journal_id, preprint, status=ChronosSubmissionStatus.DRAFT.value):
        """Serialize an OSF preprint for submission to Chronos

        It is currently unclear what ARTICLE_TYPE should be:
        Possible options are:
        * abstract
        * addendum
        * analytic-perspective
        * announcement
        * article-commentary
        * Book
        * brief-report
        * case-report
        * collection
        * correction
        * discussion
        * dissertation
        * editorial
        * in-brief
        * introduction
        * letter
        * meeting-report
        * news
        * oration
        * partial-retraction
        * product-review
        * rapid-communication
        * reply
        * reprint
        * research-article
        * retraction
        * review-article
        * study-protocol

        Returns:
            dict: The serialized manuscript
        """
        return {
            'AUTHORS': [
                cls.serialize_author(contrib)
                for contrib in preprint.contributor_set.filter(visible=True).select_related('user')
            ],
            'MANUSCRIPT_FILES': [
                cls.serialize_file(preprint, preprint.primary_file)
            ],
            'STATUS_CODE': status,
            'ABSTRACT': preprint.description,
            'ARTICLE_TYPE': 'research-article',  # ??
            'DOI': preprint.preprint_doi,
            'MANUSCRIPT_TITLE': preprint.title,
            'PROVIDER_MANUSCRIPT_ID': preprint._id,
            'CHRONOS_JOURNAL_ID': journal_id,
            'MANUSCRIPT_URL': preprint.url,
        }

    @classmethod
    def serialize_user(cls, user):
        return {
            'CHRONOS_USER_ID': user.chronos_user_id,
            'EMAIL': user.username,
            'GIVEN_NAME': user.given_name,
            'ORCID_ID': user.social.get('orcid', None),
            'PARTNER_USER_ID': user._id,
            'SURNAME': user.family_name,
        }

    @classmethod
    def serialize_author(cls, contributor):
        ret = cls.serialize_user(contributor.user)
        if contributor._order == 0:
            contribution = 'firstAuthor'
        else:
            contribution = 'submittingAuthor'
        ret.update({
            'CONTRIBUTION': contribution,
            'ORGANIZATION': '',
        })

        return ret

    @classmethod
    def serialize_file(cls, preprint, file_node):
        """Serialize an BaseFileNode for submission to Chronos.

        It is currently unclear what MANUSCRIPT_FILE_CATEGORY should be.
        Possible options are:
        * supplementaryMaterial
        * articleContent
        * movie
        * combinedPDF
        * PublicationFiles
        * supportingFile
        * coverLetter

        Note:
            `FILE_DOWNLOAD_URL` MUST be accessible by Chronos as it attempts to download
            all files given to it.

        Args:
            preprint: The Preprint that is being submitted
            file_node: The AbstractFileNode to serialize. Should belong to `preprint`

        Returns:
            The serialized AbstractFileNode
        """
        assert file_node.is_file

        if CHRONOS_USE_FAKE_FILE:
            file_url = CHRONOS_FAKE_FILE_URL
        else:
            file_url = get_file_download_link(file_node)

        return {
            'FILE_DOWNLOAD_URL': file_url,
            'FILE_NAME': file_node.name,
            'MANUSCRIPT_FILE_CATEGORY': 'Publication Files',
        }

class ChronosClient(object):

    def __init__(self, username=None, password=None, api_key=None, host=None):
        username = username or CHRONOS_USERNAME
        password = password or CHRONOS_PASSWORD
        api_key = api_key or CHRONOS_API_KEY
        host = host or CHRONOS_HOST
        self._client = ChronosRestClient(username, password, api_key, host=host)

    def sync_journals(self):
        journals = []
        for journal in self._client.get_journals():
            journals.append(ChronosJournal.objects.update_or_create(journal_id=journal['JOURNAL_ID'], defaults={
                'raw_response': journal,
                'title': journal['TITLE'],
                'name': journal['PUBLISHER_NAME'],
                # Other Available fields: (Not currently used for anything so they are not parsed)
                # 'E_ISSN':
                # 'ISSN':
                # 'JOURNAL_ID':
                # 'JOURNAL_URL':
                # 'PUBLISHER_ID':
                # 'PUBLISHER_NAME':
            })[0])
        return journals

    def sync_manuscript(self, submission):
        return self._sync_manuscript(
            submission,
            self._client.get_manuscript(submission.publication_id)
        )

    def get_journals(self):
        return ChronosJournal.objects.all()

    def submit_manuscript(self, journal, preprint, submitter):
        submission_qs = ChronosSubmission.objects.filter(preprint=preprint)
        if submission_qs.filter(journal=journal).exists():
            raise ValueError('{!r} already has an existing submission to {!r}.'.format(preprint, journal))

        # 1 = draft, 2 = submitted, 3 = accepted, 4 = published
        # Disallow submission if the current preprint has submissions that are submitted, accepted or publishes
        # regardless of journals
        if submission_qs.filter(status=2).exists():
            raise ValueError('Cannot submit because a pending submission exists')
        if submission_qs.filter(status=3).exists():
            raise ValueError('Cannot submit because your submission was accepted')
        if submission_qs.filter(status=4).exists():
            raise ValueError('Cannot submit because your submission was published')
        if preprint.machine_state != ReviewStates.ACCEPTED.value:
            raise ValueError('Cannot submit to Chronos if the preprint is not accepted by moderators')

        body = ChronosSerializer.serialize_manuscript(journal.journal_id, preprint)
        body['USER'] = ChronosSerializer.serialize_user(submitter)

        response = self._client.submit_manuscript(body)

        with transaction.atomic():
            submission = ChronosSubmission.objects.create(
                journal=journal,
                preprint=preprint,
                submitter=submitter,
                raw_response=response,
                # Things parsed out of response
                publication_id=response['PUBLICATION_ID'],
                status=response['STATUS_CODE'],
                submission_url=response['CHRONOS_SUBMISSION_URL'],
            )

            submitter.chronos_user_id = response['USER']['CHRONOS_USER_ID']
            submitter.save()

            for contrib, author in zip(preprint.contributor_set.filter(visible=True).select_related('user'), response['AUTHORS']):
                assert author['PARTNER_USER_ID'] == contrib.user._id
                contrib.user.chronos_user_id = author['CHRONOS_USER_ID']
                contrib.user.save()

        return submission

    def update_manuscript(self, submission):
        body = ChronosSerializer.serialize_manuscript(submission.journal.journal_id, submission.preprint, status=submission.status)
        body['USER'] = ChronosSerializer.serialize_user(submission.submitter)
        body['PUBLICATION_ID'] = submission.publication_id

        return self._sync_manuscript(
            submission,
            self._client.update_manuscript(body),
        )

    def _sync_manuscript(self, submission, response):
        with transaction.atomic():
            # TODO pick of any interesting fields
            submission.status = response['STATUS_CODE']
            # Not present when fetching from the API
            if response['CHRONOS_SUBMISSION_URL']:
                submission.submission_url = response['CHRONOS_SUBMISSION_URL']
            submission.save()
        return submission


class ChronosRestClient(object):

    def __init__(self, username, password, api_key, host='https://sandbox.api.chronos-oa.com'):
        self._auth_key = None
        self._session = requests.Session()
        self._session.verify = VERIFY_CHRONOS_SSL_CERT

        self._api_key = api_key
        self._host = host
        self._password = password
        self._username = username

    def get_journals(self):
        return self._do_request('GET', '/partners/journal/all').json()

    def submit_manuscript(self, body):
        return self._do_request('POST', '/partners/submission', json=body).json()

    def update_manuscript(self, body):
        return self._do_request('POST', '/partners/manuscript', json=body).json()

    def get_manuscript(self, manuscript_id):
        return self._do_request('GET', '/partners/manuscript/{}'.format(manuscript_id)).json()

    def get_journals_by_publisher(self, publisher):
        raise NotImplementedError

    def get_journals_by_issn(self, issn):
        raise NotImplementedError

    def _refresh_auth_key(self):
        if not self._auth_key:
            resp = self._session.post(
                '{}/partners/login'.format(self._host),
                json={
                    'password': self._password,
                    'username': self._username,
                },
                headers={
                    'api_key': self._api_key,
                },
            )
            resp.raise_for_status()
            self._auth_key = resp.json()['auth_key']
        return self._auth_key

    def _do_request(self, method, path, json=None):
        self._refresh_auth_key()

        resp = self._session.request(
            method,
            '{}{}'.format(self._host, path),
            json=json,
            headers={
                'api_key': self._api_key,
                'auth_key': self._auth_key,
            }
        )

        resp.raise_for_status()

        return resp
