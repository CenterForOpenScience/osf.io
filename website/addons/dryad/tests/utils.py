import httpretty
from json import dumps
from furl import furl

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from framework.auth import Auth

from website.addons.dryad.model import DryadProvider
from website.addons.dryad.settings import DRYAD_BASE_URL

dryad_metadata_path = furl(DRYAD_BASE_URL)
dryad_metadata_path.path.segments = ['mn', 'object', 'doi:10.5061/dryad.1850']
dryad_meta_url = dryad_metadata_path.url

dryad_list_url = furl(DRYAD_BASE_URL)
dryad_list_url.path.segments = ['mn', 'object']

response_dict = {
    dryad_meta_url: u"""
        <DryadDataPackage xmlns="http://purl.org/dryad/schema/terms/v3.1" xmlns:dwc="http://rs.tdwg.org/dwc/terms/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:bibo="http://purl.org/dryad/schema/dryad-bibo/v3.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://purl.org/dryad/schema/terms/v3.1 http://datadryad.org/profile/v3.1/dryad.xsd">
        <dcterms:type>package</dcterms:type>
        <dcterms:creator>Delsuc</dcterms:creator>
        <dcterms:creator>Tsagkogeorga, Georgia</dcterms:creator>
        <dcterms:creator>Lartillot, Nicolas</dcterms:creator>
        <dcterms:creator>Philippe</dcterms:creator>
        <dcterms:dateSubmitted>2010-08-10T13:17:46Z</dcterms:dateSubmitted>
        <dcterms:available>2010-08-10T13:17:46Z</dcterms:available>
        <dcterms:title>
        Data from: Additional molecular support for the new chordate phylogeny
        </dcterms:title>
        <dcterms:identifier>http://dx.doi.org/10.5061/dryad.1850</dcterms:identifier>
        <dcterms:description>
        Recent phylogenomic analyses have suggested tunicates instead of cephalochordates as the closest living relatives of vertebrates. In direct contradiction with the long accepted view of Euchordates, this new phylogenetic hypothesis for chordate evolution has been the object of some skepticism. We assembled an expanded phylogenomic dataset focused on deuterostomes. Maximum-likelihood using standard models and Bayesian phylogenetic analyses using the CAT site-heterogeneous mixture model of amino-acid replacement both provided unequivocal support for the sister-group relationship between tunicates and vertebrates (Olfactores). Chordates were recovered as monophyletic with cephalochordates as the most basal lineage. These results were robust to both gene sampling and missing data. New analyses of ribosomal rRNA also recovered Olfactores when compositional bias was alleviated. Despite the inclusion of 25 taxa representing all major lineages, the monophyly of deuterostomes remained poorly supported. The implications of these phylogenetic results for interpreting chordate evolution are discussed in light of recent advances from evolutionary developmental biology and genomics.
        </dcterms:description>
        <dcterms:subject>phylogenomics</dcterms:subject>
        <dcterms:subject>deuterostomes</dcterms:subject>
        <dcterms:subject>chordates</dcterms:subject>
        <dcterms:subject>tunicates</dcterms:subject>
        <dcterms:subject>cephalochordates</dcterms:subject>
        <dcterms:subject>olfactores</dcterms:subject>
        <dcterms:subject>ribosomal RNA</dcterms:subject>
        <dcterms:subject>jackknife</dcterms:subject>
        <dcterms:subject>evolution</dcterms:subject>
        <dwc:scientificName>Metazoa</dwc:scientificName>
        <dwc:scientificName>Deuterostomia</dwc:scientificName>
        <dwc:scientificName>Chordata</dwc:scientificName>
        <dwc:scientificName>Tunicata</dwc:scientificName>
        <dwc:scientificName>Urochordata</dwc:scientificName>
        <dwc:scientificName>Cephalochordata</dwc:scientificName>
        <dwc:scientificName>Hemichordata</dwc:scientificName>
        <dwc:scientificName>Xenoturbella</dwc:scientificName>
        <dwc:scientificName>Oikopleura</dwc:scientificName>
        <dwc:scientificName>Ciona</dwc:scientificName>
        <dwc:scientificName>Vertebrata</dwc:scientificName>
        <dwc:scientificName>Craniata</dwc:scientificName>
        <dwc:scientificName>Cyclostomata</dwc:scientificName>
        <dcterms:temporal>Phanerozoic</dcterms:temporal>
        <dcterms:references>http://dx.doi.org/10.1002/dvg.20450</dcterms:references>
        <dcterms:hasPart>http://dx.doi.org/10.5061/dryad.1850/1</dcterms:hasPart>
        </DryadDataPackage>
        """,
    dryad_list_url.url: u"""
        <d1:objectList xmlns:d1="http://ns.dataone.org/service/types/v1" start="0" total="79954" count="20">
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.9025?ver=2011-03-31T12:10:27.130-04:00
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">1fa39305aa5e12ad178763e6cece5869</checksum>
        <dateSysMetadataModified>2011-03-31T12:10:27.130-04:00</dateSysMetadataModified>
        <size>4172</size>
        </objectInfo>
        <objectInfo>
        <identifier>http://dx.doi.org/10.5061/dryad.9025</identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">12216e38ef78bfadb3c039bc0d5717fd</checksum>
        <dateSysMetadataModified>2011-03-31T12:10:27.130-04:00</dateSysMetadataModified>
        <size>6528</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.db8hd?ver=2011-04-25T11:45:10.173-04:00
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">ca41b2ce881bf73e34675c60689dec4a</checksum>
        <dateSysMetadataModified>2011-04-25T11:45:10.173-04:00</dateSysMetadataModified>
        <size>2952</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.db8hd
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">e385778fe64c1d49c3007721ab89515e</checksum>
        <dateSysMetadataModified>2011-04-25T11:45:10.173-04:00</dateSysMetadataModified>
        <size>8529</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.7pb8s?ver=2011-04-25T12:00:29.882-04:00
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">6589a80561a69376874a17d884504810</checksum>
        <dateSysMetadataModified>2011-04-25T12:00:29.882-04:00</dateSysMetadataModified>
        <size>3296</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.7pb8s
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">e056531cfc485893efaea1c1dd90eaf8</checksum>
        <dateSysMetadataModified>2011-04-25T12:00:29.882-04:00</dateSysMetadataModified>
        <size>10497</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.023g3
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">773844a3a5f1b9565029b3cd33ce5565</checksum>
        <dateSysMetadataModified>2011-04-26T16:52:59.420-04:00</dateSysMetadataModified>
        <size>3420</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.023g3
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">472b44c86766ac24f95871f5bd5ac2c2</checksum>
        <dateSysMetadataModified>2011-04-26T16:52:59.420-04:00</dateSysMetadataModified>
        <size>4593</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.6h722
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">0a17545430c4f7c4155a3859865fe5f7</checksum>
        <dateSysMetadataModified>2011-04-27T16:56:53.784-04:00</dateSysMetadataModified>
        <size>2817</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.6h722
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">92605947ec0ca4a3459b159662005a4e</checksum>
        <dateSysMetadataModified>2011-04-27T16:56:53.784-04:00</dateSysMetadataModified>
        <size>4593</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.1fh61?ver=2011-04-28T16:25:30.180-04:00
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">037f8914b191f2ab4d70755a6c8209f5</checksum>
        <dateSysMetadataModified>2011-04-28T16:25:30.180-04:00</dateSysMetadataModified>
        <size>3243</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.1fh61
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">3727fa02ed966841efc2f5a1ba68a9b2</checksum>
        <dateSysMetadataModified>2011-04-28T16:25:30.180-04:00</dateSysMetadataModified>
        <size>4593</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.gn1v3
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">d99f6f859bb9037fc027d1f7a5e3d0da</checksum>
        <dateSysMetadataModified>2011-05-09T14:10:28.610-04:00</dateSysMetadataModified>
        <size>4699</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.gn1v3
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">06577b79078e52cb248fb73515c339e5</checksum>
        <dateSysMetadataModified>2011-05-09T14:10:28.610-04:00</dateSysMetadataModified>
        <size>34169</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.jq989
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">a07aeb466a0491a923c8a2b1c0164d0d</checksum>
        <dateSysMetadataModified>2011-05-17T14:28:09.005-04:00</dateSysMetadataModified>
        <size>3784</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.jq989
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">33a5605a447f2a68231eaab834867037</checksum>
        <dateSysMetadataModified>2011-05-17T14:28:09.005-04:00</dateSysMetadataModified>
        <size>4593</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.j1fd7
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">d66d2dcf62513ec0393c8c9fe85d96cc</checksum>
        <dateSysMetadataModified>2011-05-19T11:24:59.521-04:00</dateSysMetadataModified>
        <size>1831</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.j1fd7
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">3753ecd5239929ef2b36f318c97aea7b</checksum>
        <dateSysMetadataModified>2011-05-19T11:24:59.521-04:00</dateSysMetadataModified>
        <size>6561</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.3td2f
        </identifier>
        <formatId>http://datadryad.org/profile/v3.1</formatId>
        <checksum algorithm="MD5">6d75a7b5860179b5d56ddd7f17e9cabc</checksum>
        <dateSysMetadataModified>2011-05-26T12:37:54.043-04:00</dateSysMetadataModified>
        <size>2700</size>
        </objectInfo>
        <objectInfo>
        <identifier>
        http://dx.doi.org/10.5061/dryad.3td2f
        </identifier>
        <formatId>http://www.openarchives.org/ore/terms</formatId>
        <checksum algorithm="MD5">8639aed07c4128f979e34d526899d0ca</checksum>
        <dateSysMetadataModified>2011-05-26T12:37:54.043-04:00</dateSysMetadataModified>
        <size>6561</size>
        </objectInfo>
        </d1:objectList>
        """,
    dryad_meta_url + '1': """
            <DryadDataFile xmlns="http://purl.org/dryad/schema/terms/v3.1"
            xmlns:dwc="http://rs.tdwg.org/dwc/terms/"
            xmlns:dcterms="http://purl.org/dc/terms/"
            xmlns:bibo="http://purl.org/dryad/schema/dryad-bibo/v3.1"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://purl.org/dryad/schema/terms/v3.1
            http://datadryad.org/profile/v3.1/dryad.xsd">
            <dcterms:type>file</dcterms:type>
            <dcterms:creator>Delsuc</dcterms:creator>
            <dcterms:creator>Tsagkogeorga, Georgia</dcterms:creator>
            <dcterms:creator>Lartillot, Nicolas</dcterms:creator>
            <dcterms:creator>Philippe, Herv</dcterms:creator>
            <dcterms:title>Delsuc2008-Genesis.nex</dcterms:title>
            <dcterms:identifier>http://dx.doi.org/10.5061/dryad.1850/1</dcterms:identifier>
            <dcterms:rights>http://creativecommons.org/publicdomain/zero/1.0/</dcterms:rights>
            <dcterms:subject>phylogenomics</dcterms:subject>
            <dcterms:subject>deuterostomes</dcterms:subject>
            <dcterms:subject>chordates</dcterms:subject>
            <dcterms:subject>tunicates</dcterms:subject>
            <dcterms:subject>cephalochordates</dcterms:subject>
            <dcterms:subject>olfactores</dcterms:subject>
            <dcterms:subject>ribosomal RNA</dcterms:subject>
            <dcterms:subject>jackknife</dcterms:subject>
            <dcterms:subject>evolution</dcterms:subject>
            <dwc:scientificName>Metazoa</dwc:scientificName>
            <dwc:scientificName>Deuterostomia</dwc:scientificName>
            <dwc:scientificName>Chordata</dwc:scientificName>
            <dwc:scientificName>Tunicata</dwc:scientificName>
            <dwc:scientificName>Urochordata</dwc:scientificName>
            <dwc:scientificName>Cephalochordata</dwc:scientificName>
            <dwc:scientificName>Hemichordata</dwc:scientificName>
            <dwc:scientificName>Xenoturbella</dwc:scientificName>
            <dwc:scientificName>Oikopleura</dwc:scientificName>
            <dwc:scientificName>Ciona</dwc:scientificName>
            <dwc:scientificName>Vertebrata</dwc:scientificName>
            <dwc:scientificName>Craniata</dwc:scientificName>
            <dwc:scientificName>Cyclostomata</dwc:scientificName>
            <dcterms:temporal>Phanerozoic</dcterms:temporal>
            <dcterms:dateSubmitted>2010-08-10T13:17:40Z</dcterms:dateSubmitted>
            <dcterms:available>2010-08-10T13:17:40Z</dcterms:available>
            <dcterms:provenance>
            Made available in DSpace on 2010-08-10T13:17:40Z (GMT). No. of bitstreams: 1
             Delsuc2008-Genesis.nex: 2874855 bytes, checksum: 1ccd4f33cf0e67cdc859a2b969fd99bf (MD5)
            </dcterms:provenance>
            <dcterms:isPartOf>http://dx.doi.org/10.5061/dryad.1850</dcterms:isPartOf>
            </DryadDataFile>"""}

def setup_httpretty():
    for key, value in response_dict.iteritems():
        httpretty.register_uri(
            httpretty.GET,
            key,
            body=dumps(value)
        )


class BadTestResponse:
    status_code = 404
    text = ''


class GoodResponse:
    status_code = 200
    text = ''


class DryadTestRepository(DryadProvider):

    def get(self, url='localhost', params={}):
        try:
            resp = GoodResponse()
            resp.text = response_dict[url]
            return resp
        except KeyError:
            return BadTestResponse()

    def post(self, url):
        pass

class DryadTestCase(OsfTestCase):

    def setUp(self):
        super(DryadTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('dryad', auth=Auth(self.user))
        self.project.creator.add_addon('dryad')
        self.node_settings = self.project.get_addon('dryad')
        self.user_settings = self.project.creator.get_addon('dryad')
        self.user_settings.save()
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()
