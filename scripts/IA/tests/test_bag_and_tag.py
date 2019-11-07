import os
import json
import unittest
import responses
HERE = os.path.dirname(os.path.abspath(__file__))
from nose.tools import assert_equal
import xml.etree.ElementTree as ET

from scripts.IA.bag_and_tag import build_metadata


def node_metadata():
    with open(os.path.join(HERE, 'fixtures/metadata-resp-with-embeds.json'), 'r') as fp:
        return json.loads(fp.read())


class TestWikiDumper(unittest.TestCase):

    @responses.activate
    def test_build_metadata(self):
        xml = build_metadata(node_metadata()['data'])
        root = ET.fromstring(xml)
        ret_xml = [(child.tag, child.attrib) for child in root]

        # This is the XML!
        assert_equal(('{http://datacite.org/schema/kernel-4}identifier', {'identifierType': 'DOI'}), ret_xml[0])
        assert_equal(('{http://datacite.org/schema/kernel-4}creators', {}), ret_xml[1])
        assert_equal(('{http://datacite.org/schema/kernel-4}titles', {}), ret_xml[2])
        assert_equal(('{http://datacite.org/schema/kernel-4}publisher', {}), ret_xml[3])
        assert_equal(('{http://datacite.org/schema/kernel-4}publicationYear', {}), ret_xml[4])
        assert_equal(('{http://datacite.org/schema/kernel-4}resourceType', {'resourceTypeGeneral': 'Text'}), ret_xml[5])
        assert_equal(('{http://datacite.org/schema/kernel-4}rightsList', {}), ret_xml[6])

        for data in root.findall('{http://datacite.org/schema/kernel-4}identifier'):
            assert_equal(data.text, '10.31219/osf.io/8gqkv')

        for data in root.findall('{http://datacite.org/schema/kernel-4}creators'):
            title = data.find('{http://datacite.org/schema/kernel-4}creator').find('{http://datacite.org/schema/kernel-4}creatorName').text
            assert_equal(title, 'John Tordoff')

        for data in root.findall('{http://datacite.org/schema/kernel-4}titles'):
            title = data.find('{http://datacite.org/schema/kernel-4}title').text
            assert_equal(title, 'Test Component')

        for data in root.findall('{http://datacite.org/schema/kernel-4}publisher'):
            assert_equal(data.text, 'Open Science Framework')

        for data in root.findall('{http://datacite.org/schema/kernel-4}publicationYear'):
            assert_equal(data.text, '2019')

        for data in root.findall('{http://datacite.org/schema/kernel-4}resourceType'):
            assert_equal(data.text, 'Registration')

        for data in root.findall('{http://datacite.org/schema/kernel-4}rightsList'):
            rights = data.find('{http://datacite.org/schema/kernel-4}rights').text
            assert_equal(rights, 'CC0 1.0 Universal')
