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
            'project_created_year': project.created.year,
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
        project.node_license.year = '2250-2254'
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
        format_kwargs['file_created_year'] = file.created.year
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
      "contributorName": "Center for Open Science",
      "contributorType": "HostingInstitution",
      "name": "Center for Open Science",
      "nameIdentifiers": [
        {{
          "name": "Center for Open Science",
          "nameIdentifier": "https://ror.org/05d5mza29",
          "nameIdentifierScheme": "ROR"
        }},
        {{
          "name": "Center for Open Science",
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
  "publisher": "OSF",
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
  <publisher>OSF</publisher>
  <publicationYear>2252</publicationYear>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Center for Open Science</contributorName>
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

BASIC_TURTLE = '''@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://localhost:5000/{project_id}> a osf:Project ;
    dcterms:created "{date}" ;
    dcterms:creator <http://localhost:5000/{user_id}> ;
    dcterms:dateCopyrighted "2252" ;
    dcterms:description "this is a project description!" ;
    dcterms:identifier "http://localhost:5000/{project_id}",
        "https://doi.org/10.70102/FK2osf.io/{project_id}" ;
    dcterms:modified "{date}" ;
    dcterms:publisher <http://localhost:5000/> ;
    dcterms:rights "No license" ;
    dcterms:rightsHolder "Me",
        "You" ;
    dcterms:title "this is a project title!" ;
    owl:sameAs <https://doi.org/10.70102/FK2osf.io/{project_id}> .

<http://localhost:5000/{user_id}> a osf:Agent ;
    dcterms:identifier "http://localhost:5000/{user_id}" ;
    dcterms:type foaf:Person ;
    foaf:name "Person McNamington" .

<http://localhost:5000/> a osf:Agent ;
    dcterms:identifier "http://localhost:5000/" ;
    dcterms:type foaf:Organization ;
    foaf:name "OSF" .'''


COMPLICATED_DATACITE_JSON = '''{{
  "contributors": [
    {{
      "contributorName": "Center for Open Science",
      "contributorType": "HostingInstitution",
      "name": "Center for Open Science",
      "nameIdentifiers": [
        {{
          "name": "Center for Open Science",
          "nameIdentifier": "https://ror.org/05d5mza29",
          "nameIdentifierScheme": "ROR"
        }},
        {{
          "name": "Center for Open Science",
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
  "publicationYear": "{project_created_year}",
  "publisher": "OSF",
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
  <publisher>OSF</publisher>
  <publicationYear>{project_created_year}</publicationYear>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Center for Open Science</contributorName>
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

COMPLICATED_TURTLE = '''@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://localhost:5000/{project_id}> a osf:Project ;
    dcterms:created "{date}" ;
    dcterms:creator <http://localhost:5000/{user_id}> ;
    dcterms:dateCopyrighted "2250-2254" ;
    dcterms:description "this is a project description!" ;
    dcterms:identifier "http://localhost:5000/{project_id}",
        "https://doi.org/10.70102/FK2osf.io/{project_id}" ;
    dcterms:language "es" ;
    dcterms:modified "{date}" ;
    dcterms:publisher <http://localhost:5000/> ;
    dcterms:rights <https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode> ;
    dcterms:rightsHolder "Me",
        "You" ;
    dcterms:title "this is a project title!" ;
    dcterms:type "Dataset" ;
    owl:sameAs <https://doi.org/10.70102/FK2osf.io/{project_id}> ;
    osf:contains <http://localhost:5000/{file_id}> ;
    osf:funder [ a osf:FundingReference ;
            dcterms:identifier "https://doi.org/10.$$$$" ;
            foaf:name "Mx. Moneypockets" ;
            osf:awardNumber "10000000" ;
            osf:awardTitle "because reasons" ;
            osf:awardUri "https://moneypockets.example/millions" ;
            osf:funderIdentifierType "Crossref Funder ID" ] .

<http://localhost:5000/{file_id}> a osf:File ;
    dcterms:created "{date}" ;
    dcterms:identifier "http://localhost:5000/{file_id}" ;
    dcterms:modified "{date}" ;
    osf:fileName "my-file.blarg" ;
    osf:filePath "/my-file.blarg" ;
    osf:isContainedBy <http://localhost:5000/{project_id}> .

<http://localhost:5000/{user_id}> a osf:Agent ;
    dcterms:identifier "http://localhost:5000/{user_id}" ;
    dcterms:type foaf:Person ;
    foaf:name "Person McNamington" .

<http://localhost:5000/> a osf:Agent ;
    dcterms:identifier "http://localhost:5000/" ;
    dcterms:type foaf:Organization ;
    foaf:name "OSF" .

<https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode> foaf:name "CC-By Attribution-NonCommercial-NoDerivatives 4.0 International" .'''


FILE_TURTLE = '''@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://localhost:5000/{file_id}> a osf:File ;
    dcterms:created "{date}" ;
    dcterms:hasVersion <http://localhost:8000/v2/files/{raw_file_id}/versions/1/> ;
    dcterms:identifier "http://localhost:5000/{file_id}" ;
    dcterms:modified "{date}" ;
    osf:fileName "my-file.blarg" ;
    osf:filePath "/my-file.blarg" ;
    osf:isContainedBy <http://localhost:5000/{project_id}> .

<http://localhost:8000/v2/files/{raw_file_id}/versions/1/> a osf:FileVersion ;
    dcterms:created "{date}" ;
    dcterms:creator <http://localhost:5000/{user_id}> ;
    dcterms:extent "0.000007 MB" ;
    dcterms:format "img/png" ;
    dcterms:modified "{date}" ;
    dcterms:requires <urn:checksum:sha-256::6ac3c336e4094835293a3fed8a4b5fedde1b5e2626d9838fed50693bba00af0e> ;
    osf:versionNumber "1" .

<http://localhost:5000/{project_id}> a osf:Project ;
    dcterms:created "{date}" ;
    dcterms:creator <http://localhost:5000/{user_id}> ;
    dcterms:identifier "http://localhost:5000/{project_id}",
        "https://doi.org/10.70102/FK2osf.io/{project_id}" ;
    dcterms:title "this is a project title!" ;
    dcterms:type "Dataset" ;
    owl:sameAs <https://doi.org/10.70102/FK2osf.io/{project_id}> .

<http://localhost:5000/{user_id}> a osf:Agent ;
    dcterms:identifier "http://localhost:5000/{user_id}" ;
    dcterms:type foaf:Person ;
    foaf:name "Person McNamington" .'''


FILE_DATACITE_JSON = '''{{
  "contributors": [
    {{
      "contributorName": "Center for Open Science",
      "contributorType": "HostingInstitution",
      "name": "Center for Open Science",
      "nameIdentifiers": [
        {{
          "name": "Center for Open Science",
          "nameIdentifier": "https://ror.org/05d5mza29",
          "nameIdentifierScheme": "ROR"
        }},
        {{
          "name": "Center for Open Science",
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
      "identifier": "http://localhost:5000/{file_id}",
      "identifierType": "URL"
    }}
  ],
  "publicationYear": "{file_created_year}",
  "publisher": "OSF",
  "relatedIdentifiers": [
    {{
      "relatedIdentifier": "http://localhost:8000/v2/files/{raw_file_id}/versions/1/",
      "relatedIdentifierType": "URL",
      "relationType": "HasVersion"
    }},
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
  <publisher>OSF</publisher>
  <publicationYear>{file_created_year}</publicationYear>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Center for Open Science</contributorName>
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
    <relatedIdentifier relatedIdentifierType="URL" relationType="HasVersion">http://localhost:8000/v2/files/{raw_file_id}/versions/1/</relatedIdentifier>
    <relatedIdentifier relatedIdentifierType="URL" relationType="IsPartOf">http://localhost:5000/{project_id}</relatedIdentifier>
  </relatedIdentifiers>
</resource>
'''
