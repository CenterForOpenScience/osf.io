from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.guid.model import BlacklistGuid
from tests.base import OsfTestCase
from scripts.add_blacklist_guids import create_blacklist_guid_objects


class TestBlacklistGuids(OsfTestCase):

    def test_create_whitelist_db_items(self):
        clean_list = ['bad']
        create_blacklist_guid_objects(clean_list)
        try:
            guid = BlacklistGuid.find_one(Q('_id', 'eq', 'bad'))
        except NoResultsFound:
            assert False