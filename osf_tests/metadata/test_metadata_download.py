from api_tests.utils import create_test_file
from osf.models import GuidMetadataRecord
from osf.models.licenses import NodeLicense
from osf_tests import factories
from tests.base import OsfTestCase


class TestMetadataDownload(OsfTestCase):
    def test_metadata_download(self):
        user = factories.AuthUserFactory(
            fullname='Person McNamington',
        )
        project = factories.ProjectFactory(
            creator=user,
            title='this is a project title!',
            description='this is a project description!',
            node_license=factories.NodeLicenseRecordFactory(
                node_license=NodeLicense.objects.get(
                    name='No license',
                ),
                year='2252',
                copyright_holders=['Me', 'You'],
            ),
        )
        project.set_identifier_value(category='doi', value=f'10.70102/FK2osf.io/{project._id}')

        # unauthed, private project
        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-json')
        assert resp.status_code == 302

        today = project.created.date()
        format_kwargs = {
            'project_id': project._id,
            'user_id': user._id,
            'date': str(today),
        }

        resp = self.app.get(f'/{project._id}/metadata/?format=turtle', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'text/turtle'
        assert resp.content_disposition == f'attachment; filename={project._id}-metadata.ttl'
        assert resp.unicode_body == BASIC_TURTLE.format(**format_kwargs)

        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-json', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/json'
        assert resp.content_disposition == f'attachment; filename={project._id}-datacite.json'
        assert resp.unicode_body == BASIC_DATACITE_JSON.format(**format_kwargs)

        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-xml', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/xml'
        assert resp.content_disposition == f'attachment; filename={project._id}-datacite.xml'
        assert resp.unicode_body == BASIC_DATACITE_XML.format(**format_kwargs)

        metadata_record = GuidMetadataRecord.objects.for_guid(project._id)
        metadata_record.update({
            'language': 'es',
            'resource_type_general': 'Dataset',
            'funding_info': [
                {
                    'funder_name': 'Mx. Moneypockets',
                    'funder_identifier': 'https://doi.org/10.$$$$',
                    'funder_identifier_type': 'Crossref Funder ID',
                    'award_number': '10000000',
                    'award_uri': 'https://moneypockets.example/millions',
                    'award_title': 'because reasons',
                },
            ],
        }, auth=user)
        project.node_license.node_license = NodeLicense.objects.get(
            name='CC-By Attribution-NonCommercial-NoDerivatives 4.0 International',
        )
        project.node_license.save()

        file = create_test_file(
            project,
            user,
            filename='my-file.blarg',
            size=7,
            sha256='6ac3c336e4094835293a3fed8a4b5fedde1b5e2626d9838fed50693bba00af0e',
        )
        file_guid = file.get_guid()._id
        format_kwargs['file_id'] = file_guid
        format_kwargs['raw_file_id'] = file._id
        format_kwargs['fileversion_id'] = file.versions.first().identifier

        resp = self.app.get(f'/{project._id}/metadata/?format=turtle', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'text/turtle'
        assert resp.content_disposition == f'attachment; filename={project._id}-metadata.ttl'
        assert resp.unicode_body == COMPLICATED_TURTLE.format(**format_kwargs)

        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-json', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/json'
        assert resp.content_disposition == f'attachment; filename={project._id}-datacite.json'
        assert resp.unicode_body == COMPLICATED_DATACITE_JSON.format(**format_kwargs)

        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-xml', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/xml'
        assert resp.content_disposition == f'attachment; filename={project._id}-datacite.xml'
        assert resp.unicode_body == COMPLICATED_DATACITE_XML.format(**format_kwargs)

        ### now check that file
        format_kwargs['year'] = str(today.year)
        resp = self.app.get(f'/{file_guid}/metadata/?format=turtle', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'text/turtle'
        assert resp.content_disposition == f'attachment; filename={file_guid}-metadata.ttl'
        assert resp.unicode_body == FILE_TURTLE.format(**format_kwargs)

        resp = self.app.get(f'/{file_guid}/metadata/?format=datacite-json', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/json'
        assert resp.content_disposition == f'attachment; filename={file_guid}-datacite.json'
        assert resp.unicode_body == FILE_DATACITE_JSON.format(**format_kwargs)

        resp = self.app.get(f'/{file_guid}/metadata/?format=datacite-xml', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/xml'
        assert resp.content_disposition == f'attachment; filename={file_guid}-datacite.xml'
        assert resp.unicode_body == FILE_DATACITE_XML.format(**format_kwargs)


# doubled {{}} cleaned by a call to .format()
BASIC_DATACITE_JSON = '''{{
  "contributors": [
    {{
      "contributorName": "Open Science Framework",
      "contributorType": "HostingInstitution",
      "name": "Open Science Framework",
      "nameIdentifiers": [
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://ror.org/05d5mza29",
          "nameIdentifierScheme": "ROR"
        }},
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://grid.ac/institutes/grid.466501.0/",
          "nameIdentifierScheme": "GRID"
        }}
      ],
      "nameType": "Organizational"
    }}
  ],
  "creators": [
    {{
      "affiliation": [],
      "name": "Person McNamington",
      "nameIdentifiers": [
        {{
          "nameIdentifier": "http://localhost:5000/{user_id}",
          "nameIdentifierScheme": "URL"
        }}
      ],
      "nameType": "Personal"
    }}
  ],
  "dates": [
    {{
      "date": "{date}",
      "dateType": "Created"
    }},
    {{
      "date": "{date}",
      "dateType": "Updated"
    }}
  ],
  "descriptions": [
    {{
      "description": "this is a project description!",
      "descriptionType": "Abstract"
    }}
  ],
  "fundingReferences": [],
  "identifiers": [
    {{
      "identifier": "10.70102/FK2osf.io/{project_id}",
      "identifierType": "DOI"
    }},
    {{
      "identifier": "http://localhost:5000/{project_id}",
      "identifierType": "URL"
    }}
  ],
  "publicationYear": "2252",
  "publisher": "Open Science Framework",
  "relatedIdentifiers": [],
  "rightsList": [
    {{
      "rights": "No license"
    }}
  ],
  "schemaVersion": "http://datacite.org/schema/kernel-4",
  "subjects": [],
  "titles": [
    {{
      "title": "this is a project title!"
    }}
  ],
  "types": {{
    "resourceType": "Project",
    "resourceTypeGeneral": "Text"
  }}
}}'''


BASIC_DATACITE_XML = '''<?xml version='1.0' encoding='utf-8'?>
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.3/metadata.xsd">
  <identifier identifierType="DOI">10.70102/FK2osf.io/{project_id}</identifier>
  <alternateIdentifiers>
    <alternateIdentifier alternateIdentifierType="URL">http://localhost:5000/{project_id}</alternateIdentifier>
  </alternateIdentifiers>
  <creators>
    <creator>
      <creatorName nameType="Personal">Person McNamington</creatorName>
      <nameIdentifier nameIdentifierScheme="URL">http://localhost:5000/{user_id}</nameIdentifier>
    </creator>
  </creators>
  <titles>
    <title>this is a project title!</title>
  </titles>
  <publisher>Open Science Framework</publisher>
  <publicationYear>2252</publicationYear>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Open Science Framework</contributorName>
      <nameIdentifier nameIdentifierScheme="ROR">https://ror.org/05d5mza29</nameIdentifier>
      <nameIdentifier nameIdentifierScheme="GRID">https://grid.ac/institutes/grid.466501.0/</nameIdentifier>
    </contributor>
  </contributors>
  <dates>
    <date dateType="Created">{date}</date>
    <date dateType="Updated">{date}</date>
  </dates>
  <resourceType resourceTypeGeneral="Text">Project</resourceType>
  <rightsList>
    <rights>No license</rights>
  </rightsList>
  <descriptions>
    <description descriptionType="Abstract">this is a project description!</description>
  </descriptions>
</resource>
'''

BASIC_TURTLE = '''@prefix dct: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://localhost:5000/{project_id}> a osf:Project ;
    dct:created "{date}" ;
    dct:creator <http://localhost:5000/{user_id}> ;
    dct:dateCopyrighted "2252" ;
    dct:description "this is a project description!" ;
    dct:identifier "http://localhost:5000/{project_id}",
        "https://doi.org/10.70102/FK2osf.io/{project_id}" ;
    dct:modified "{date}" ;
    dct:rights "No license" ;
    dct:rightsHolder "Me",
        "You" ;
    dct:title "this is a project title!" ;
    dct:type osf:project ;
    owl:sameAs <https://doi.org/10.70102/FK2osf.io/{project_id}> .

<http://localhost:5000/{user_id}> a dct:Agent,
        osf:OSFUser ;
    dct:identifier "http://localhost:5000/{user_id}" ;
    foaf:name "Person McNamington" .

'''


COMPLICATED_DATACITE_JSON = '''{{
  "contributors": [
    {{
      "contributorName": "Open Science Framework",
      "contributorType": "HostingInstitution",
      "name": "Open Science Framework",
      "nameIdentifiers": [
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://ror.org/05d5mza29",
          "nameIdentifierScheme": "ROR"
        }},
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://grid.ac/institutes/grid.466501.0/",
          "nameIdentifierScheme": "GRID"
        }}
      ],
      "nameType": "Organizational"
    }}
  ],
  "creators": [
    {{
      "affiliation": [],
      "name": "Person McNamington",
      "nameIdentifiers": [
        {{
          "nameIdentifier": "http://localhost:5000/{user_id}",
          "nameIdentifierScheme": "URL"
        }}
      ],
      "nameType": "Personal"
    }}
  ],
  "dates": [
    {{
      "date": "{date}",
      "dateType": "Created"
    }},
    {{
      "date": "{date}",
      "dateType": "Updated"
    }}
  ],
  "descriptions": [
    {{
      "description": "this is a project description!",
      "descriptionType": "Abstract"
    }}
  ],
  "fundingReferences": [
    {{
      "awardNumber": "10000000",
      "awardTitle": "because reasons",
      "awardURI": "https://moneypockets.example/millions",
      "funderIdentifier": "https://doi.org/10.$$$$",
      "funderIdentifierType": "Crossref Funder ID",
      "funderName": "Mx. Moneypockets"
    }}
  ],
  "identifiers": [
    {{
      "identifier": "10.70102/FK2osf.io/{project_id}",
      "identifierType": "DOI"
    }},
    {{
      "identifier": "http://localhost:5000/{project_id}",
      "identifierType": "URL"
    }}
  ],
  "language": "es",
  "publicationYear": "2252",
  "publisher": "Open Science Framework",
  "relatedIdentifiers": [],
  "rightsList": [
    {{
      "rights": "CC-By Attribution-NonCommercial-NoDerivatives 4.0 International",
      "rightsUri": "https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode"
    }}
  ],
  "schemaVersion": "http://datacite.org/schema/kernel-4",
  "subjects": [],
  "titles": [
    {{
      "title": "this is a project title!"
    }}
  ],
  "types": {{
    "resourceType": "Project",
    "resourceTypeGeneral": "Dataset"
  }}
}}'''


COMPLICATED_DATACITE_XML = '''<?xml version='1.0' encoding='utf-8'?>
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.3/metadata.xsd">
  <identifier identifierType="DOI">10.70102/FK2osf.io/{project_id}</identifier>
  <alternateIdentifiers>
    <alternateIdentifier alternateIdentifierType="URL">http://localhost:5000/{project_id}</alternateIdentifier>
  </alternateIdentifiers>
  <creators>
    <creator>
      <creatorName nameType="Personal">Person McNamington</creatorName>
      <nameIdentifier nameIdentifierScheme="URL">http://localhost:5000/{user_id}</nameIdentifier>
    </creator>
  </creators>
  <titles>
    <title>this is a project title!</title>
  </titles>
  <publisher>Open Science Framework</publisher>
  <publicationYear>2252</publicationYear>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Open Science Framework</contributorName>
      <nameIdentifier nameIdentifierScheme="ROR">https://ror.org/05d5mza29</nameIdentifier>
      <nameIdentifier nameIdentifierScheme="GRID">https://grid.ac/institutes/grid.466501.0/</nameIdentifier>
    </contributor>
  </contributors>
  <dates>
    <date dateType="Created">{date}</date>
    <date dateType="Updated">{date}</date>
  </dates>
  <language>es</language>
  <resourceType resourceTypeGeneral="Dataset">Project</resourceType>
  <rightsList>
    <rights rightsURI="https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode">CC-By Attribution-NonCommercial-NoDerivatives 4.0 International</rights>
  </rightsList>
  <descriptions>
    <description descriptionType="Abstract">this is a project description!</description>
  </descriptions>
  <fundingReferences>
    <fundingReference>
      <funderName>Mx. Moneypockets</funderName>
      <funderIdentifier funderIdentifierType="Crossref Funder ID">https://doi.org/10.$$$$</funderIdentifier>
      <awardNumber>10000000</awardNumber>
      <awardTitle>because reasons</awardTitle>
    </fundingReference>
  </fundingReferences>
</resource>
'''

COMPLICATED_TURTLE = '''@prefix dct: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://localhost:5000/{project_id}> a osf:Project ;
    dct:created "{date}" ;
    dct:creator <http://localhost:5000/{user_id}> ;
    dct:dateCopyrighted "2252" ;
    dct:description "this is a project description!" ;
    dct:hasPart <http://localhost:5000/{file_id}> ;
    dct:identifier "http://localhost:5000/{project_id}",
        "https://doi.org/10.70102/FK2osf.io/{project_id}" ;
    dct:language "es" ;
    dct:modified "{date}" ;
    dct:rights <https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode> ;
    dct:rightsHolder "Me",
        "You" ;
    dct:title "this is a project title!" ;
    dct:type osf:project,
        "Dataset" ;
    owl:sameAs <https://doi.org/10.70102/FK2osf.io/{project_id}> ;
    osf:funder [ a osf:Funder ;
            dct:identifier "https://doi.org/10.$$$$" ;
            foaf:name "Mx. Moneypockets" ;
            osf:award_number "10000000" ;
            osf:award_title "because reasons" ;
            osf:award_uri "https://moneypockets.example/millions" ;
            osf:funder_identifier_type "Crossref Funder ID" ] ;
    osf:has_file <http://localhost:5000/{file_id}> .

<http://localhost:5000/{user_id}> a dct:Agent,
        osf:OSFUser ;
    dct:identifier "http://localhost:5000/{user_id}" ;
    foaf:name "Person McNamington" .

<https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode> foaf:name "CC-By Attribution-NonCommercial-NoDerivatives 4.0 International" .

<http://localhost:5000/{file_id}> a osf:File ;
    dct:created "{date}" ;
    dct:identifier "http://localhost:5000/{file_id}" ;
    dct:modified "{date}" ;
    osf:file_name "my-file.blarg" ;
    osf:file_path "/my-file.blarg" .

'''


FILE_TURTLE = '''@prefix dct: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://localhost:5000/{file_id}> a osf:File ;
    dct:created "{date}" ;
    dct:hasVersion <http://localhost:8000/v2/files/{raw_file_id}/versions/{fileversion_id}/> ;
    dct:identifier "http://localhost:5000/{file_id}" ;
    dct:isPartOf <http://localhost:5000/{project_id}> ;
    dct:modified "{date}" ;
    osf:file_name "my-file.blarg" ;
    osf:file_path "/my-file.blarg" .

<http://localhost:5000/{project_id}> a osf:Project ;
    dct:created "{date}" ;
    dct:creator <http://localhost:5000/{user_id}> ;
    dct:dateCopyrighted "2252" ;
    dct:description "this is a project description!" ;
    dct:identifier "http://localhost:5000/{project_id}",
        "https://doi.org/10.70102/FK2osf.io/{project_id}" ;
    dct:language "es" ;
    dct:modified "{date}" ;
    dct:rights <https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode> ;
    dct:rightsHolder "Me",
        "You" ;
    dct:title "this is a project title!" ;
    dct:type osf:project,
        "Dataset" ;
    owl:sameAs <https://doi.org/10.70102/FK2osf.io/{project_id}> ;
    osf:funder [ a osf:Funder ;
            dct:identifier "https://doi.org/10.$$$$" ;
            foaf:name "Mx. Moneypockets" ;
            osf:award_number "10000000" ;
            osf:award_title "because reasons" ;
            osf:award_uri "https://moneypockets.example/millions" ;
            osf:funder_identifier_type "Crossref Funder ID" ] .

<http://localhost:8000/v2/files/{raw_file_id}/versions/{fileversion_id}/> a osf:FileVersion ;
    dct:created "{date}" ;
    dct:creator <http://localhost:5000/{user_id}> ;
    dct:extent "0.000007 MB" ;
    dct:format "img/png" ;
    dct:modified "{date}" ;
    dct:requires <urn:checksum:sha-256::6ac3c336e4094835293a3fed8a4b5fedde1b5e2626d9838fed50693bba00af0e> ;
    osf:version_number "1" .

<https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode> foaf:name "CC-By Attribution-NonCommercial-NoDerivatives 4.0 International" .

<http://localhost:5000/{user_id}> a dct:Agent,
        osf:OSFUser ;
    dct:identifier "http://localhost:5000/{user_id}" ;
    foaf:name "Person McNamington" .

'''


FILE_DATACITE_JSON = '''{{
  "contributors": [
    {{
      "contributorName": "Open Science Framework",
      "contributorType": "HostingInstitution",
      "name": "Open Science Framework",
      "nameIdentifiers": [
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://ror.org/05d5mza29",
          "nameIdentifierScheme": "ROR"
        }},
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://grid.ac/institutes/grid.466501.0/",
          "nameIdentifierScheme": "GRID"
        }}
      ],
      "nameType": "Organizational"
    }}
  ],
  "creators": [
    {{
      "affiliation": [],
      "name": "Person McNamington",
      "nameIdentifiers": [
        {{
          "nameIdentifier": "http://localhost:5000/{user_id}",
          "nameIdentifierScheme": "URL"
        }}
      ],
      "nameType": "Personal"
    }}
  ],
  "dates": [
    {{
      "date": "{date}",
      "dateType": "Created"
    }},
    {{
      "date": "{date}",
      "dateType": "Updated"
    }}
  ],
  "descriptions": [],
  "fundingReferences": [],
  "identifiers": [
    {{
      "identifier": "",
      "identifierType": "DOI"
    }},
    {{
      "identifier": "http://localhost:5000/{file_id}",
      "identifierType": "URL"
    }}
  ],
  "publicationYear": "{year}",
  "publisher": "Open Science Framework",
  "relatedIdentifiers": [
    {{
      "relatedIdentifier": "http://localhost:5000/{project_id}",
      "relatedIdentifierType": "URL",
      "relationType": "IsPartOf"
    }}
  ],
  "rightsList": [],
  "schemaVersion": "http://datacite.org/schema/kernel-4",
  "subjects": [],
  "titles": [
    {{
      "title": "my-file.blarg"
    }}
  ],
  "types": {{
    "resourceType": "File",
    "resourceTypeGeneral": "Text"
  }}
}}'''


FILE_DATACITE_XML = '''<?xml version='1.0' encoding='utf-8'?>
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.3/metadata.xsd">
  <identifier identifierType="DOI"></identifier>
  <alternateIdentifiers>
    <alternateIdentifier alternateIdentifierType="URL">http://localhost:5000/{file_id}</alternateIdentifier>
  </alternateIdentifiers>
  <creators>
    <creator>
      <creatorName nameType="Personal">Person McNamington</creatorName>
      <nameIdentifier nameIdentifierScheme="URL">http://localhost:5000/{user_id}</nameIdentifier>
    </creator>
  </creators>
  <titles>
    <title>my-file.blarg</title>
  </titles>
  <publisher>Open Science Framework</publisher>
  <publicationYear>{year}</publicationYear>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Open Science Framework</contributorName>
      <nameIdentifier nameIdentifierScheme="ROR">https://ror.org/05d5mza29</nameIdentifier>
      <nameIdentifier nameIdentifierScheme="GRID">https://grid.ac/institutes/grid.466501.0/</nameIdentifier>
    </contributor>
  </contributors>
  <dates>
    <date dateType="Created">{date}</date>
    <date dateType="Updated">{date}</date>
  </dates>
  <resourceType resourceTypeGeneral="Text">File</resourceType>
  <relatedIdentifiers>
    <relatedIdentifier relatedIdentifierType="URL" relationType="IsPartOf">http://localhost:5000/{project_id}</relatedIdentifier>
  </relatedIdentifiers>
</resource>
'''
