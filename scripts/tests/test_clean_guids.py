import os
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.guid.model import CleanGuid, Guid
from tests.base import OsfTestCase
from scripts.clean_guids import remove_current_guids, create_clean_guid_objects
from nose.tools import *  # noqa PEP8 asserts


class TestCleanGuids(OsfTestCase):

    def test_remove_current_guids(self):
        guid = Guid(_id='guid1')
        guid.save()
        clean_guids = remove_current_guids('test_files/test_clean_guids.csv')
        assert_not_in('guid1', clean_guids)

    def test_create_whitelist_db_items(self):
        clean_list = ['clean']
        create_clean_guid_objects(clean_list)
        try:
            guid = CleanGuid.find_one(Q('_id', 'eq', 'clean'))
        except NoResultsFound:
            assert False