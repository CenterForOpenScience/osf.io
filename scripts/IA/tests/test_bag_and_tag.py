import os
import mock
import json
import unittest
import responses
import xml.etree.ElementTree as ET
from nose.tools import assert_equal, assert_in
from scripts.IA.bag_and_tag import build_metadata, write_metadata_and_bag

HERE = os.path.dirname(os.path.abspath(__file__))


def node_metadata():
    with open(os.path.join(HERE, 'fixtures/metadata-resp-with-embeds.json'), 'r') as fp:
        return json.loads(fp.read())


def datacite_xml():
    with open(os.path.join(HERE, 'fixtures/datacite-metadata.xml'), 'r') as fp:
        return fp.read()


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
            assert_equal(title, 'Brian Dawkins')

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

    @mock.patch('scripts.IA.bag_and_tag.bagit.make_bag')
    def test_bag_and_tag(self, mock_bagit):
        with mock.patch('builtins.open', mock.mock_open()) as m:
            write_metadata_and_bag(datacite_xml(), 'tests/test_directory')
            m.assert_called_with(os.path.join(HERE, 'test_directory/datacite.xml'), 'w')
            assert_in('osf.io/scripts/IA/tests/test_directory', mock_bagit.call_args_list[0][0][0])
