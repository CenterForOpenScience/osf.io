
# To change this template, choose Tools | Templates
# and open the template in the editor.
__author__="peterbull"
__date__ ="$Jul 30, 2013 12:21:28 PM$"

# python base lib modules
import mimetypes
import os
import pprint
from zipfile import ZipFile

# downloaded modules
import sword2

# local modules
from file import DvnFile
from utils import format_term, get_elements, DvnException


class Study(object):
    def __init__(self, *args, **kwargs):

        # adds dict to keyword arguments
        kwargs = dict(args[0].items() + kwargs.items()) if args and isinstance(args[0], dict) else kwargs

        # deposit receipt is added when Dataverse.add_study() is called on this study
        self.lastDepositReceipt = None

        # sets fields from kwargs
        self.editUri = kwargs.pop('editUri') if 'editUri' in kwargs.keys() else None
        self.editMediaUri = kwargs.pop('editMediaUri') if 'editMediaUri' in kwargs.keys() else None
        self.statementUri = kwargs.pop('statementUri') if 'statementUri' in kwargs.keys() else None

        # todo: add self.exists_on_dataverse / self.created
        self.hostDataverse = kwargs.pop('hostDataverse') if 'hostDataverse' in kwargs.keys() else None

        # creates sword entry from xml
        if args and not isinstance(args[0], dict):
            with open(args[0]) as f:
                xml = f.read()
            self.entry = sword2.Entry(xml)

        # creates sword entry from keyword arguments
        if kwargs:
            if 'title' not in kwargs.keys() or isinstance(kwargs.get('title'), list):
                raise Exception('Study needs a single, valid title.')

            self.entry = sword2.Entry()

            for k in kwargs.keys():
                if isinstance(kwargs[k], list):
                    for item in kwargs[k]:
                        self.entry.add_field(format_term(k), item)
                else:
                    self.entry.add_field(format_term(k), kwargs[k])

    def __repr__(self):
        studyObject = pprint.pformat(self.__dict__)
        entryObject = self.entry.pretty_print()
        return """STUDY ========= "
        study=
{so}
        
        entry=
{eo}
/STUDY ========= """.format(so=studyObject,eo=entryObject)

    @classmethod
    def from_entry_element(cls, entry_element, hostDataverse=None):
        id_element = get_elements(entry_element,
                                  tag="id",
                                  numberOfElements=1)
                                    
        title_element = get_elements(entry_element,
                                     tag="title",
                                     numberOfElements=1)
                                            
        edit_media_link_element = get_elements(entry_element,
                                               tag="link",
                                               attribute="rel",
                                               attributeValue="edit-media",
                                               numberOfElements=1)

        edit_media_link = edit_media_link_element.get("href") if edit_media_link_element is not None else None

        return cls(title=title_element.text,
                   id=id_element.text,
                   editUri=entry_element.base,   # edit iri
                   editMediaUri=edit_media_link,
                   hostDataverse=hostDataverse)  # edit-media iri
                   
    def get_statement(self):
        if not self.statementUri:
            atomXml = self.get_entry()
            statementLink = get_elements(atomXml,
                                         tag="link",
                                         attribute="rel",
                                         attributeValue="http://purl.org/net/sword/terms/statement",
                                         numberOfElements=1)
            self.statementUri = statementLink.get("href")
        
        studyStatement = self.hostDataverse.connection.swordConnection.get_resource(self.statementUri).content
        return studyStatement

    def get_entry(self):
        return self.hostDataverse.connection.swordConnection.get_resource(self.editUri).content

    def get_file(self, file_name):
        for f in self.get_files():
            if file_name == f.name:
                return f

    def get_files(self):
        if not self.statementUri:
            atomXml = self.get_entry()
            statementLink = get_elements(atomXml,
                                         tag="link",
                                         attribute="rel",
                                         attributeValue="http://purl.org/net/sword/terms/statement",
                                         numberOfElements=1)
            self.statementUri = statementLink.get("href")

        atomStatement = self.hostDataverse.connection.swordConnection.get_atom_sword_statement(self.statementUri)

        return [DvnFile.CreateFromAtomStatementObject(res, self) for res in atomStatement.resources]
        
    def add_file(self, filepath):
        self.add_files([filepath])

    def add_files(self, filepaths):
        # convert a directory to a list of files
        if len(filepaths) == 1 and os.path.isdir(filepaths[0]):
            filepaths = self._open_directory(filepaths[0])

        # Todo: Handle file versions
        for filepath in filepaths:
            filename = os.path.basename(filepath)
            if os.path.getsize(filepath) < 5:
                raise DvnException('The DataVerse does not currently accept files less than 5 bytes. '
                                   '{} cannot be uploaded.'.format(filename))
            elif filename in [f.name for f in self.get_files()]:
                raise DvnException('The file {} already exists on the DataVerse'.format(filename))

        print "Uploading files: ", filepaths
        
        deleteAfterUpload = False

        # if we have more than one file, or one file that is not a zip, we need to zip it
        if len(filepaths) != 1 or mimetypes.guess_type(filepaths[0])[0] != "application/zip":
            filepath = self._zip_files(filepaths)
            deleteAfterUpload = True
        else:
            filepath = filepaths[0]

        filename = os.path.basename(filepath)

        with open(filepath, "rb") as pkg:
            depositReceipt = self.hostDataverse.connection.swordConnection.add_file_to_resource(
                edit_media_iri=self.editMediaUri,
                payload=pkg,
                mimetype='application/zip',
                filename=filename,
                packaging='http://purl.org/net/sword/package/SimpleZip',
            )

            self._refresh(deposit_receipt=depositReceipt)

        if deleteAfterUpload:
            os.remove(filepath)    
    
    def update_metadata(self):
        #todo: consumer has to use the methods on self.entry (from sword2.atom_objects) to update the
        # metadata before calling this method. that's a little cumbersome...
        depositReceipt = self.hostDataverse.connection.swordConnection.update(
            dr=self.lastDepositReceipt,
            edit_iri=self.editUri,
            edit_media_iri=self.editMediaUri,
            metadata_entry=self.entry,
        )
        self._refresh(deposit_receipt=depositReceipt)
    
    def release(self):
        self.lastDepositReceipt = self.hostDataverse.connection.swordConnection.complete_deposit(
            dr=self.lastDepositReceipt,
            se_iri=self.editUri,
        )
        self._refresh(deposit_receipt=self.lastDepositReceipt)
    
    def delete_file(self, dvnFile):
        depositReceipt = self.hostDataverse.connection.swordConnection.delete(dvnFile.editMediaUri)
        self._refresh(deposit_receipt=self.lastDepositReceipt)
        
    def delete_all_files(self):
        for f in self.get_files():
            self.delete_file(f)
        
    def get_citation(self):
        return get_elements(self.get_entry(), namespace="http://purl.org/dc/terms/", tag="bibliographicCitation",
                            numberOfElements=1).text
    
    def get_state(self):
        return get_elements(self.get_statement(), tag="category", attribute="term",
                            attributeValue="latestVersionState", numberOfElements=1).text
    
    def get_id(self):
        urlPieces = self.editMediaUri.rsplit("/")
        return '/'.join([urlPieces[-2], urlPieces[-1]])
    
    def _zip_files(self, filesToZip, pathToStoreZip=None):
        zipFilePath = os.path.join(os.getenv("TEMP", "/tmp"),  "temp_dvn_upload.zip") \
            if not pathToStoreZip else pathToStoreZip
        
        zipFile = ZipFile(zipFilePath, 'w')
        for fileToZip in filesToZip:
            zipFile.write(fileToZip)
        zipFile.close()
            
        return zipFilePath

    def _open_directory(self, path):
        path = os.path.normpath(path) + os.sep
        filepaths = []
        for filename in os.listdir(path):
            filepath = path + filename
            if os.path.isdir(filepath):
                filepaths += self._open_directory(filepath)
            else:
                filepaths.append(filepath)
        return filepaths

    # if we perform a server operation, we should refresh the study object
    def _refresh(self, deposit_receipt=None):
        # todo is it possible for the deposit receipt to have different info than the study?
        if deposit_receipt:
            self.editUri = deposit_receipt.edit
            self.editMediaUri = deposit_receipt.edit_media
            self.statementUri = deposit_receipt.atom_statement_iri
            self.lastDepositReceipt = deposit_receipt
        self.entry = sword2.Entry(atomEntryXml=self.get_entry())