# -*- coding: utf-8 -*-
import furl
import lxml
import time
import logging

import requests
from django.db.models import QuerySet

from framework.auth.utils import impute_names
from website.identifiers.utils import remove_control_characters
from website.identifiers.clients.base import AbstractIdentifierClient
from website import settings

logger = logging.getLogger(__name__)

CROSSREF_NAMESPACE = 'http://www.crossref.org/schema/4.4.1'
CROSSREF_SCHEMA_LOCATION = 'http://www.crossref.org/schema/4.4.1 http://www.crossref.org/schemas/crossref4.4.1.xsd'
CROSSREF_ACCESS_INDICATORS = 'http://www.crossref.org/AccessIndicators.xsd'
CROSSREF_RELATIONS = 'http://www.crossref.org/relations.xsd'
CROSSREF_SCHEMA_VERSION = '4.4.1'
JATS_NAMESPACE = 'http://www.ncbi.nlm.nih.gov/JATS1'
XSI = 'http://www.w3.org/2001/XMLSchema-instance'
CROSSREF_DEPOSITOR_NAME = 'Open Science Framework'

CROSSREF_SUFFIX_LIMIT = 10
CROSSREF_SURNAME_LIMIT = 60
CROSSREF_GIVEN_NAME_LIMIT = 60

class CrossRefClient(AbstractIdentifierClient):

    def __init__(self, base_url):
        self.base_url = base_url

    def get_credentials(self):
        return (settings.CROSSREF_USERNAME, settings.CROSSREF_PASSWORD)

    def build_doi(self, preprint):
        from osf.models import PreprintProvider

        prefix = preprint.provider.doi_prefix or PreprintProvider.objects.get(_id='osf').doi_prefix
        return settings.DOI_FORMAT.format(prefix=prefix, guid=preprint._id)

    def build_metadata(self, preprint, status='public', include_relation=True, **kwargs):
        """Return the crossref metadata XML document for a given preprint as a string for DOI minting purposes

        :param preprint: the preprint, or list of preprints to build metadata for
        """
        is_batch = False
        if isinstance(preprint, (list, QuerySet)):
            is_batch = True
            preprints = preprint
        else:
            preprints = [preprint]

        element = lxml.builder.ElementMaker(nsmap={
            None: CROSSREF_NAMESPACE,
            'xsi': XSI},
        )

        # batch_id is used to get the guid of preprints for error messages down the line
        # but there is a size limit -- for bulk requests, include only the first 5 guids
        batch_id = ','.join([prep._id for prep in preprints[:5]])

        head = element.head(
            element.doi_batch_id(batch_id),
            element.timestamp(str(int(time.time()))),
            element.depositor(
                element.depositor_name(CROSSREF_DEPOSITOR_NAME),
                element.email_address(settings.CROSSREF_DEPOSITOR_EMAIL)
            ),
            element.registrant('Center for Open Science')
        )
        # if this is a batch update, let build_posted_content determine status for each preprint
        status = status if not is_batch else None
        body = element.body()
        for preprint in preprints:
            body.append(self.build_posted_content(preprint, element, status, include_relation))

        root = element.doi_batch(
            head,
            body,
            version=CROSSREF_SCHEMA_VERSION
        )
        root.attrib['{%s}schemaLocation' % XSI] = CROSSREF_SCHEMA_LOCATION
        return lxml.etree.tostring(root, pretty_print=kwargs.get('pretty_print', True))

    def build_posted_content(self, preprint, element, status, include_relation):
        """Build the <posted_content> element for a single preprint
        preprint - preprint to build posted_content for
        element - namespace element to use when building parts of the XML structure
        """
        status = status or self.get_status(preprint)
        posted_content = element.posted_content(
            element.group_title(preprint.provider.name),
            type='preprint'
        )
        if status == 'public':
            posted_content.append(element.contributors(*self._crossref_format_contributors(element, preprint)))

        title = element.title(remove_control_characters(preprint.title)) if status == 'public' else element.title('')
        posted_content.append(element.titles(title))

        posted_content.append(element.posted_date(*self._crossref_format_date(element, preprint.date_published)))

        if status == 'public':
            posted_content.append(element.item_number('osf.io/{}'.format(preprint._id)))

            if preprint.description:
                posted_content.append(
                    element.abstract(element.p(remove_control_characters(preprint.description)), xmlns=JATS_NAMESPACE))

            if preprint.license and preprint.license.node_license.url:
                posted_content.append(
                    element.program(
                        element.license_ref(preprint.license.node_license.url,
                                            start_date=preprint.date_published.strftime('%Y-%m-%d')),
                        xmlns=CROSSREF_ACCESS_INDICATORS
                    )
                )
            else:
                posted_content.append(
                    element.program(xmlns=CROSSREF_ACCESS_INDICATORS)
                )

            if preprint.article_doi and include_relation:
                posted_content.append(
                    element.program(
                        element.related_item(
                            element.intra_work_relation(
                                preprint.article_doi,
                                **{'relationship-type': 'isPreprintOf', 'identifier-type': 'doi'}
                            )
                        ), xmlns=CROSSREF_RELATIONS
                    )
                )

        doi = self.build_doi(preprint)
        doi_data = [
            element.doi(doi),
            element.resource(settings.DOMAIN + preprint._id)
        ]
        posted_content.append(element.doi_data(*doi_data))

        return posted_content

    def _process_crossref_name(self, contributor):
        # Adapted from logic used in `api/citations/utils.py`
        # If the user has a family and given name, use those
        if contributor.family_name and contributor.given_name:
            given = contributor.given_name
            middle = contributor.middle_names
            family = contributor.family_name
            suffix = contributor.suffix
        else:
            names = impute_names(contributor.fullname)
            given = names.get('given')
            middle = names.get('middle')
            family = names.get('family')
            suffix = names.get('suffix')

        given_name = ' '.join([given, middle]).strip()
        given_stripped = remove_control_characters(given_name)
        # For crossref, given_name is not allowed to have numbers or question marks
        given_processed = ''.join(
            [char for char in given_stripped if (not char.isdigit() and char != '?')]
        )
        surname_processed = remove_control_characters(family)

        surname = surname_processed or given_processed or contributor.fullname
        processed_names = {'surname': surname[:CROSSREF_SURNAME_LIMIT].strip()}
        if given_processed and surname_processed:
            processed_names['given_name'] = given_processed[:CROSSREF_GIVEN_NAME_LIMIT].strip()
        if suffix and (surname_processed or given_processed):
            processed_names['suffix'] = suffix[:CROSSREF_SUFFIX_LIMIT].strip()

        return processed_names

    def _crossref_format_contributors(self, element, preprint):
        contributors = []
        for index, contributor in enumerate(preprint.visible_contributors):
            if index == 0:
                sequence = 'first'
            else:
                sequence = 'additional'
            name_parts = self._process_crossref_name(contributor)
            person = element.person_name(sequence=sequence, contributor_role='author')
            if name_parts.get('given_name'):
                person.append(element.given_name(name_parts['given_name']))
            person.append(element.surname(name_parts['surname']))
            if name_parts.get('suffix'):
                person.append(element.suffix(remove_control_characters(name_parts['suffix'])))
            if contributor.external_identity.get('ORCID'):
                orcid = contributor.external_identity['ORCID'].keys()[0]
                verified = contributor.external_identity['ORCID'].values()[0] == 'VERIFIED'
                if orcid and verified:
                    person.append(
                        element.ORCID('https://orcid.org/{}'.format(orcid), authenticated='true')
                    )
            contributors.append(person)

        return contributors

    def _crossref_format_date(self, element, date):
        elements = [
            element.month(date.strftime('%m')),
            element.day(date.strftime('%d')),
            element.year(date.strftime('%Y'))
        ]
        return elements

    def _build_url(self, **query):
        url = furl.furl(self.base_url)
        url.args.update(query)
        return url.url

    def create_identifier(self, preprint, category, include_relation=True):
        status = self.get_status(preprint)

        if category == 'doi':
            metadata = self.build_metadata(preprint, status, include_relation)
            doi = self.build_doi(preprint)
            filename = doi.split('/')[-1]
            username, password = self.get_credentials()
            logger.info('Sending metadata for DOI {}:\n{}'.format(doi, metadata))

            # Crossref sends an email to CROSSREF_DEPOSITOR_EMAIL to confirm
            requests.request(
                'POST',
                self._build_url(
                    operation='doMDUpload',
                    login_id=username,
                    login_passwd=password,
                    fname='{}.xml'.format(filename)
                ),
                files={'file': ('{}.xml'.format(filename), metadata)},
            )

            # Don't wait for response to confirm doi because it arrives via email.
            return {'doi': doi}
        else:
            raise NotImplementedError()

    def update_identifier(self, preprint, category):
        return self.create_identifier(preprint, category)

    def get_status(self, preprint):
        return 'public' if preprint.verified_publishable and not preprint.is_retracted else 'unavailable'

    def bulk_create(self, metadata, filename):
        # Crossref sends an email to CROSSREF_DEPOSITOR_EMAIL to confirm
        username, password = self.get_credentials()
        requests.request(
            'POST',
            self._build_url(
                operation='doMDUpload',
                login_id=username,
                login_passwd=password,
                fname='{}.xml'.format(filename)
            ),
            files={'file': ('{}.xml'.format(filename), metadata)},
        )

        logger.info('Sent a bulk update of metadata to CrossRef')


class ECSArXivCrossRefClient(CrossRefClient):

    def get_credentials(self):
        return (settings.ECSARXIV_CROSSREF_USERNAME, settings.ECSARXIV_CROSSREF_PASSWORD)
