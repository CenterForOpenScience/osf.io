CLIENT_ID = None
CLIENT_SECRET = None

SCOPE = ['repo']

SET_PRIVACY = False

#DRYAD OAI-PMH metadata harvesting settings
#Note where requested, format as (date, prefix, dataset)
DRYAD_OAI_IDENTIFY = "http://www.datadryad.org/oai/request?verb=Identify"
DRYAD_OAI_LISTSET = "http://www.datadryad.org/oai/request?verb=ListSets"
DRYAD_OAI_LISTMETADATAFORMAT = "http://www.datadryad.org/oai/request?verb=ListMetadataFormats"
DRYAD_OAI_LISTIDENTIFIERS = "http://www.datadryad.org/oai/request?verb=ListIdentifiers&from={}&metadataPrefix={}&set={}"
DRYAD_OAI_LISTRECORDS = "http://www.datadryad.org/oai/request?verb=ListRecords&from={}&metadataPrefix={}&set={}"
DRYAD_OAI_GETRECORD = "www.datadryad.org/oai/request?verb=GetRecord&identifier={}&metadataPrefix={}"
DRYAD_OAI_RESUMPTION = "http://www.datadryad.org/oai/request?verb=ListRecords&resumptionToken={}"

#Dataone API
DRYAD_DATAONE_LIST = "http://www.datadryad.org/mn/object?start={}&count={}"
DRYAD_DATAONE_METADATA = "https://datadryad.org/mn/object/doi:{}"
DRYAD_DATAONE_DOWNLOAD = "https://datadryad.org/mn/object/doi:{}/bitstream"

#SOLR Search Query
DRYAD_SOLR_SEARCH = "http://datadryad.org/solr/search/select/?q={}"

CACHE = False

WATERBUTLER_CREDENTIALS = {
    'storage': {}
}

WATERBUTLER_SETTINGS = {}
