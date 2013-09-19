__author__="peterbull"
__date__ ="$Jul 30, 2013 12:32:24 PM$"

# python base lib modules
import pprint

#downloaded modules
from lxml import etree

#local modules
from study import Study
import utils

class Dataverse(object):
    # todo rename connection to dvn_connection?
    def __init__(self, connection, collection):
        self.connection = connection
        self.collection = collection
        
    def __repr__(self):
        return pprint.saferepr(self.__dict__)

    # Note: is_released is a Dataverse concept--not from SWORD
    # todo: make property
    def is_released(self):
        # Get entry resource for collection
        collectionInfo = self.connection.swordConnection.get_resource(self.collection.href).content
        status = utils.get_elements(
            collectionInfo,
            namespace="http://purl.org/net/sword/terms/state",
            tag="dataverseHasBeenReleased",
            numberOfElements=1
        ).text
        return bool(status)

    def add_study(self, study):        
        depositReceipt = self.connection.swordConnection.create(
            metadata_entry=study.entry,
            col_iri=self.collection.href
        )
                                                     
        study.hostDataverse = self
        # todo: study.exists = True
        study._refresh(deposit_receipt=depositReceipt)
        
    def delete_study(self, study):
        depositReceipt = self.connection.swordConnection.delete(study.editUri)
        study.isDeleted = True

    # Note: Functionality removed
    # def delete_all_studies(self, bigHammer=False, ignoreExceptions=False):
    #     # big hammer deletes all of the contents of a dataverse. this is dev only
    #     # code that will be removed before release and big hammer will stop working
    #     if bigHammer:
    #         self.connection.swordConnection.delete(self.collection.href)
    #     else:
    #         studies = self.get_studies()
    #         for s in studies:
    #             try:
    #                 self.delete_study(s)
    #             except Exception as e:
    #                 if not ignoreExceptions:
    #                     raise e
        
    def get_studies(self):
        studiesResponse = self.connection.swordConnection.get_resource(self.collection.href)

        return [
            Study.CreateStudyFromEntryElement(element, hostDataverse=self)
            for element in utils.get_elements(studiesResponse.content, tag='entry')
        ]
        # # get all the entry nodes and parse them into study objects
        # studies = []
        # for element in utils.get_elements(studiesResponse.content, tag="entry"):
        #     s = Study.CreateStudyFromEntryElement(element, hostDataverse=self)
        #     studies.append(s)
        #
        # return studies

    # todo: search by handle, DOI, etc
    # todo: rename to global_id
    def get_study_by_hdl(self, hdl):
        studies = self.get_studies()
        
        #TODO peterbull: Regex hdl to make sure it is a valid handle
        
        for s in studies:
            if hdl in s.editUri:
                return s
        return None
    
    def get_study_by_string_in_entry(self, string):
        studies = self.get_studies()
        
        for s in studies:
            if string in s.entry.pretty_print():
                return s
        return None
    