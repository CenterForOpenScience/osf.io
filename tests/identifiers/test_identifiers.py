# -*- coding: utf-8 -*-
from nose.tools import *  # noqa

from django.db import IntegrityError

from osf_tests.factories import (
    SubjectFactory,
    AuthUserFactory,
    PreprintFactory,
    IdentifierFactory,
    RegistrationFactory,
    PreprintProviderFactory
)

from tests.base import OsfTestCase

import lxml.etree

from website import settings
from website.identifiers import metadata
from osf.models import Identifier, Subject, NodeLicense


class TestMetadataGeneration(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.visible_contrib = AuthUserFactory()
        visible_contrib2 = AuthUserFactory(given_name=u'ヽ༼ ಠ益ಠ ༽ﾉ', family_name=u'ლ(´◉❥◉｀ლ)')
        self.invisible_contrib = AuthUserFactory()
        self.node = RegistrationFactory(is_public=True)
        self.identifier = Identifier(referent=self.node, category='catid', value='cat:7')
        self.node.add_contributor(self.visible_contrib, visible=True)
        self.node.add_contributor(self.invisible_contrib, visible=False)
        self.node.add_contributor(visible_contrib2, visible=True)
        self.node.save()

    # This test is not used as datacite is currently used for nodes, leaving here for future reference
    def test_datacite_metadata_for_preprint_has_correct_structure(self):
        provider = PreprintProviderFactory()
        license =  NodeLicense.objects.get(name="CC-By Attribution 4.0 International")
        license_details = {
            'id': license.license_id,
            'year': '2017',
            'copyrightHolders': ['Jeff Hardy', 'Matt Hardy']
        }
        preprint = PreprintFactory(provider=provider, project=self.node, is_published=True, license_details=license_details)
        metadata_xml = metadata.datacite_metadata_for_preprint(preprint, doi=preprint.get_identifier('doi').value, pretty_print=True)

        root = lxml.etree.fromstring(metadata_xml)
        xsi_location = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
        expected_location = 'http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd'
        assert root.attrib[xsi_location] == expected_location

        identifier = root.find('{%s}identifier' % metadata.NAMESPACE)
        assert identifier.attrib['identifierType'] == 'DOI'
        assert identifier.text == preprint.get_identifier('doi').value

        creators = root.find('{%s}creators' % metadata.NAMESPACE)
        assert len(creators.getchildren()) == len(self.node.visible_contributors)

        subjects = root.find('{%s}subjects' % metadata.NAMESPACE)
        assert subjects.getchildren()

        publisher = root.find('{%s}publisher' % metadata.NAMESPACE)
        assert publisher.text == provider.name

        pub_year = root.find('{%s}publicationYear' % metadata.NAMESPACE)
        assert pub_year.text == str(preprint.date_published.year)

        dates = root.find('{%s}dates' % metadata.NAMESPACE).getchildren()[0]
        assert dates.text == preprint.modified.isoformat()
        assert dates.attrib['dateType'] == 'Updated'

        alternate_identifier = root.find('{%s}alternateIdentifiers' % metadata.NAMESPACE).getchildren()[0]
        assert alternate_identifier.text == settings.DOMAIN + preprint._id
        assert alternate_identifier.attrib['alternateIdentifierType'] == 'URL'

        descriptions = root.find('{%s}descriptions' % metadata.NAMESPACE).getchildren()[0]
        assert descriptions.text == preprint.node.description

        rights = root.find('{%s}rightsList' % metadata.NAMESPACE).getchildren()[0]
        assert rights.text == preprint.license.name

    # This test is not used as datacite is currently used for nodes, leaving here for future reference
    def test_datacite_format_creators_for_preprint(self):
        preprint = PreprintFactory(project=self.node, is_published=True)

        verified_user = AuthUserFactory(external_identity={'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}})
        linked_user = AuthUserFactory(external_identity={'ORCID': {'1234-nope-1234-nope': 'LINK'}})
        self.node.add_contributor(verified_user, visible=True)
        self.node.add_contributor(linked_user, visible=True)
        self.node.save()

        formatted_creators = metadata.format_creators(preprint)

        contributors_with_orcids = 0
        guid_identifiers = []
        for creator_xml in formatted_creators:
            assert creator_xml.find('creatorName').text != u'{}, {}'.format(self.invisible_contrib.family_name, self.invisible_contrib.given_name)

            name_identifiers = creator_xml.findall('nameIdentifier')

            for name_identifier in name_identifiers:
                if name_identifier.attrib['nameIdentifierScheme'] == 'ORCID':
                    assert name_identifier.attrib['schemeURI'] == 'http://orcid.org/'
                    contributors_with_orcids += 1
                else:
                    guid_identifiers.append(name_identifier.text)
                    assert name_identifier.attrib['nameIdentifierScheme'] == 'OSF'
                    assert name_identifier.attrib['schemeURI'] == settings.DOMAIN

        assert contributors_with_orcids >= 1
        assert len(formatted_creators) == len(self.node.visible_contributors)
        assert sorted(guid_identifiers) == sorted([contrib.absolute_url for contrib in self.node.visible_contributors])

    # This test is not used as datacite is currently used for nodes, leaving here for future reference
    def test_datacite_format_subjects_for_preprint(self):
        subject = SubjectFactory()
        subject_1 = SubjectFactory(parent=subject)
        subject_2 = SubjectFactory(parent=subject)

        subjects = [[subject._id, subject_1._id], [subject._id, subject_2._id]]
        preprint = PreprintFactory(subjects=subjects, project=self.node, is_published=True)

        formatted_subjects = metadata.format_subjects(preprint)
        assert len(formatted_subjects) == Subject.objects.all().count()


class TestIdentifierModel(OsfTestCase):

    def test_fields(self):
        node = RegistrationFactory()
        identifier = Identifier(referent=node, category='catid', value='cat:7')
        assert_equal(identifier.referent, node)
        assert_equal(identifier.category, 'catid')
        assert_equal(identifier.value, 'cat:7')

    def test_unique_constraint(self):
        node = RegistrationFactory()
        IdentifierFactory(referent=node)
        with assert_raises(IntegrityError):
            IdentifierFactory(referent=node)

    def test_mixin_get(self):
        identifier = IdentifierFactory()
        node = identifier.referent
        assert_equal(node.get_identifier(identifier.category), identifier)

    def test_mixin_get_value(self):
        identifier = IdentifierFactory()
        node = identifier.referent
        assert_equal(node.get_identifier_value(identifier.category), identifier.value)

    def test_mixin_set_create(self):
        node = RegistrationFactory()
        assert_is_none(node.get_identifier('dogid'))
        node.set_identifier_value('dogid', 'dog:1')
        assert_equal(node.get_identifier_value('dogid'), 'dog:1')

    def test_mixin_set_update(self):
        identifier = IdentifierFactory(category='dogid', value='dog:1')
        node = identifier.referent
        assert_equal(node.get_identifier_value('dogid'), 'dog:1')
        node.set_identifier_value('dogid', 'dog:2')
        assert_equal(node.get_identifier_value('dogid'), 'dog:2')

    def test_node_csl(self):
        node = RegistrationFactory()
        node.set_identifier_value('doi', 'FK424601')
        assert_equal(node.csl['DOI'], 'FK424601')
