"""
Wrapper around the sword2.Connection class.
"""

# todo exception handling
# todo PEP8

__author__="peterbull"
__date__ ="$Aug 16, 2013 12:32:24 PM$"

# python base lib modules

#downloaded modules
import sword2

#local modules
from dataverse import Dataverse


class DvnConnection(object):
    # todo add port number
    def __init__(self, username, password, host, cert=None, sdUriOverride=None, disable_ssl_certificate_validation=False):
        # Connection Properties
        self.username = username
        self.password = password
        self.host = host
        self.sdUri = "https://{host}/dvn/api/data-deposit/v1/swordv2/service-document".format(host=self.host) \
            if not sdUriOverride else sdUriOverride.format(host=self.host)
        self.cert = cert
        self.disable_ssl_certificate_validation = disable_ssl_certificate_validation
        
        # Connection Status and SWORD Properties
        self.swordConnection = None
        self.status = None
        self.connected = False
        self.serviceDocument = None
        
        # DVN Properties
        # todo delete: doesn't do anything?
        self.dataverses = None
        
        self._connect()

    # todo raise exception if connection fails?
    def _connect(self):
        self.swordConnection = sword2.Connection(
            service_document_iri=self.sdUri,
            user_name=self.username,
            user_pass=self.password,
            ca_certs=self.cert,
            disable_ssl_certificate_validation=self.disable_ssl_certificate_validation,
        )

        self.serviceDocument = self.swordConnection.get_service_document()
        self.status = self.swordConnection.history[1]['payload']['response']['status']
        self.connected = True if self.status == 200 else False
        
    def get_dataverses(self):
        # TODO peterbull: Do we need to call the API again to make sure
        # we get the latest set of collections?

        # Note: All SWORD collections are stored in the 0th workspace
        _, collections = self.swordConnection.workspaces[0]

        # Cast SWORD collections to Dataverses
        return [Dataverse(self, col) for col in collections]

    def get_dataverse(self, alias):
        return next((dataverse for dataverse in self.get_dataverses()
             if dataverse.alias == alias), None)
