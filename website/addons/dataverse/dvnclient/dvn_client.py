# DVN client for SWORD API
# Prereqs: Python, sword2 Module (available using easy_install)
# Adapted from: https://bitbucket.org/beno/python-sword2/wiki/Quickstart
# 

__author__="peterbull"
__date__ ="$Jul 29, 2013 1:38:57 PM$"

# enable logging for sword commands
import logging
logging.basicConfig(level=logging.ERROR)

# python base lib modules
import argparse
import json
from time import sleep
import traceback

#downloaded modules

#local modules
from study import Study
from connection import DvnConnection

def parse_arguments():
    parser = argparse.ArgumentParser(description='dvn_client exercises the APIs available for a DataVerse Network')
    
    # TODO peterbull: add arguments 
    # For manual connection2
#    parser.add_argument('action', choices=['create','upload'], default=None, help='Description for foo argument')
#    parser.add_argument('-u','--username', default=None, help='Description for foo argument')
#    parser.add_argument('-p','--password', default=None, help='Description for bar argument')
    
    parser.add_argument('--runTests', action="store", help='Path to a file with test definitions.')
    parser.add_argument('--config', action="store", help="Path to a file that contains configuration information.")
    return parser.parse_args()

def main():
    # Get the command line arguments.
    args = parse_arguments()
    
    if args.runTests and args.config:
        execfile(args.config, globals())
        execfile(args.runTests, globals())
    
    dv = None #declare outside so except clause has access
    try:
        dvc = DvnConnection(username=DEFAULT_USERNAME,
                        password=DEFAULT_PASSWORD, 
                        host=DEFAULT_HOST, 
                        cert=DEFAULT_CERT)
                        
        
        dvs = dvc.get_dataverses()
        for dv in dvs:
            print dv
            
        
        dv = dvs[0]
      
        # clean up the test dataverse
        #dv.delete_all_studies()
        print "RELEASED: ", dv.is_released()
        
        #s = Study.CreateStudyFromDict(PICS_OF_CATS_STUDY)
        #s = Study.CreateStudyFromAtomEntryXmlFile("/Users/peterbull/NetBeansProjects/dvn/tools/scripts/data-deposit-api/atom-entry-study.xml")
        #dv.add_study(s)
        #s.add_files([INGEST_FILES])
        #print s.get_citation()
        #print s.get_state()
        
        #sleep(3) #wait for ingest`
        
        #fs = s.get_files()
        #print "FILES: ", len(fs)
        #s.delete_file(fs[-1])
        #fs = s.get_files()
        #print "FILES: ", len(fs)
        #s.delete_all_files()
        #fs = s.get_files()
        #print "FILES: ", len(fs)
        
        #s.release()
        
        print "\n\ndvn_client succeeded"
        
    except Exception as e:
        sleep(1)
        traceback.print_exc()
        sleep(1)
        if dv:
            try:
                dv.swordConnection.history = json.dumps(dv.connection.swordConnection.history, indent=True)
            except:
                pass
            #print "Call History:\n", dv.connection.swordConnection.history

if __name__ == "__main__":
    main()
