# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__="peterbull"
__date__ ="$Aug 21, 2013 2:56:25 PM$"

from operator import eq
import os
import sys
from time import sleep
import unittest

import logging
logging.basicConfig(level=logging.ERROR)

#local modules
from study import Study
from connection import DvnConnection
    
class TestStudyOperations(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # LOAD TEST DATA
        
        print "Loading test data."
        testModulePath = os.path.dirname(__file__)
        execfile(os.path.join(testModulePath, "config.py"), globals())    #CREDS - This file is not committed.
        execfile(os.path.join(testModulePath, "tests.py"), globals())     #TEST DATA
        
        print "Connecting to DVN."
        self.dvc = DvnConnection(username=DEFAULT_USERNAME,
                        password=DEFAULT_PASSWORD, 
                        host=DEFAULT_HOST, 
                        cert=DEFAULT_CERT)
                        
        print "Getting Dataverse"
        self.dv = self.dvc.get_dataverses()[0]
        
        print "Removing any existing studies."
        self.dv.delete_all_studies(ignoreExceptions=True)
        
    def setUp(self):
        #runs before each test method
        
        #create a study for each test
        s = Study.CreateStudyFromDict(PICS_OF_CATS_STUDY)
        self.dv.add_study(s)
        id = s.get_id()
        self.s = self.dv.get_study_by_hdl(id)
        self.assertEqual(id, self.s.get_id())
        return
    
    def tearDown(self):
        try:
            self.dv.delete_study(self.s)
        finally:
            return
    
    def test_create_study_from_xml(self):
        xmlStudy = Study.CreateStudyFromAtomEntryXmlFile(ATOM_STUDY)
        self.dv.add_study(xmlStudy)
        atomStudy = self.dv.get_study_by_string_in_entry("The first study for the New England Journal of Coffee dataverse")
        self.assertTrue(atomStudy)
        self.dv.delete_study(atomStudy)
        
    def test_add_files_to_study(self):
        expected_files = ["char_r.tab",
                          "float_new_r.tab",
                          "int_r.tab",
                          "min_date_r.tab"]
        self.s.add_files([INGEST_FILES])
        sleep(3) #wait for ingest
        actual_files = [f.name for f in self.s.get_files()]
        
        expected_files.sort()
        actual_files.sort()
        
        self.assertEqual(expected_files, actual_files)
        
    def test_display_atom_entry(self):
        # this just tests we can get an entry back, but does
        # not do anything with that xml yet. however, we do use get_entry
        # in other methods so this test case is probably covered
        self.assertTrue(self.s.get_entry())
        
    def test_display_study_statement(self):
        # this just tests we can get an entry back, but does
        # not do anything with that xml yet. however, we do use get_statement
        # in other methods so this test case is probably covered
        self.assertTrue(self.s.get_statement())
    
    def test_delete_a_file(self):
        self.s.add_file(PIC_OF_CAT)
        
        #add file and confirm
        files = self.s.get_files()
        catFile = [f for f in files if f.name == "cat.jpg"]
        self.assertTrue(len(catFile) == 1)
        
        #delete file and confirm
        self.s.delete_file(catFile[0])
        files = self.s.get_files()
        catFile = [f for f in files if f.name == "cat.jpg"]
        self.assertTrue(len(catFile) == 0)
        
    def test_delete_a_study(self):
        xmlStudy = Study.CreateStudyFromAtomEntryXmlFile(ATOM_STUDY)
        self.dv.add_study(xmlStudy)
        atomStudy = self.dv.get_study_by_string_in_entry("The first study for the New England Journal of Coffee dataverse")
        self.assertTrue(atomStudy)

        startingNumberOfStudies = len(self.dv.get_studies())
        self.assertTrue(startingNumberOfStudies > 0)
        self.dv.delete_study(atomStudy)
        self.assertEqual(len(self.dv.get_studies()), startingNumberOfStudies - 1)
        
    def test_release_study(self):
        self.assertTrue(self.s.get_state() == "DRAFT")
        self.s.release()
        self.assertTrue(self.s.get_state() == "RELEASED")
        self.dv.delete_study(self.s) #this should deaccession
        self.assertTrue(self.s.get_state() == "DEACCESSIONED")
    
    def test_dataverse_released(self):
        self.assertTrue(self.dv.is_released())
    
if __name__ == "__main__":
    __file__ = sys.argv[0]
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStudyOperations)
    unittest.TextTestRunner(verbosity=2).run(suite)

