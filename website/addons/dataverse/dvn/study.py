
# To change this template, choose Tools | Templates
# and open the template in the editor.
__author__="peterbull"
__date__ ="$Jul 30, 2013 12:21:28 PM$"

# python base lib modules
import mimetypes
import os
import pprint
import StringIO
import requests
from zipfile import ZipFile

# downloaded modules
import sword2

# local modules
from file import DvnFile, ReleasedFile
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

    @property
    def doi(self):
        urlPieces = self.editMediaUri.rsplit("/")
        return '/'.join([urlPieces[-3], urlPieces[-2], urlPieces[-1]])

    @property
    def title(self):
        return get_elements(
            self.get_statement(), tag='title', numberOfElements=1
        ).text

    def get_statement(self):
        if not self.statementUri:
            atomXml = self.get_entry()
            statementLink = get_elements(
                atomXml,
                tag="link",
                attribute="rel",
                attributeValue="http://purl.org/net/sword/terms/statement",
                numberOfElements=1,
            )
            self.statementUri = statementLink.get("href")
        
        studyStatement = self.hostDataverse.connection.swordConnection.get_resource(self.statementUri).content
        return studyStatement

    def get_entry(self):
        return self.hostDataverse.connection.swordConnection.get_resource(self.editUri).content

    def get_file(self, file_name, released=False):

        # Search released study if specified; otherwise, search draft
        files = self.get_released_files() if released else self.get_files()
        return next((f for f in files if f.name == file_name), None)

    def get_file_by_id(self, file_id, released=False):

        # Search released study if specified; otherwise, search draft
        files = self.get_released_files() if released else self.get_files()
        return next((f for f in files if f.id == file_id), None)

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

    def get_released_files(self):
        '''
        Uses data sharing API to retrieve a list of files from the most
        recently released version of the study
        '''
        download_url = 'https://{0}/dvn/api/metadata/{1}'.format(
            self.hostDataverse.connection.host, self.doi
        )
        xml = requests.get(download_url).content
        elements = get_elements(xml, tag='otherMat')

        files = []
        for element in elements:
            f = ReleasedFile(
                name=element[0].text,
                uri=element.attrib.get('URI'),
                hostStudy=self,
            )
            files.append(f)

        return files

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

        with open(filepath, "rb") as content:
            self.add_file_obj(filename, content, zip=False)

        if deleteAfterUpload:
            os.remove(filepath)

    def add_file_obj(self, filename, content, zip=True):
        if zip:
            s = StringIO.StringIO()
            zipFile = ZipFile(s, 'w')
            zipFile.writestr(filename, content)
            zipFile.close()
            content = s.getvalue()

        depositReceipt = self.hostDataverse.connection.swordConnection.add_file_to_resource(
            edit_media_iri=self.editMediaUri,
            payload=content,
            mimetype='application/zip',
            filename=filename,
            packaging='http://purl.org/net/sword/package/SimpleZip'
        )

        self._refresh(deposit_receipt=depositReceipt)

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
        depositReceipt = self.hostDataverse.connection.swordConnection.complete_deposit(
            dr=self.lastDepositReceipt,
            se_iri=self.editUri,
        )
        self._refresh(deposit_receipt=depositReceipt)
    
    def delete_file(self, dvnFile):
        depositReceipt = self.hostDataverse.connection.swordConnection.delete_file(
            dvnFile.editMediaUri
        )
        # Dataverse does not give a desposit receipt at this time
        self._refresh(deposit_receipt=None)
        
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