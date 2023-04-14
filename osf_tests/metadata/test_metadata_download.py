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
        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-xml')
        assert resp.status_code == 302

        today = project.created.date()
        format_kwargs = {
            'project_id': project._id,
            'user_id': user._id,
            'date': str(today),
            'license_year': project.node_license.year,
            'project_created_year': project.created.year,
        }

        resp = self.app.get(f'/{project._id}/metadata/?format=turtle', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'text/turtle'
        assert resp.content_disposition == f'attachment; filename={project._id}-metadata.ttl'
        assert resp.unicode_body == BASIC_TURTLE.format(**format_kwargs)

        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-xml', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/xml'
        assert resp.content_disposition == f'attachment; filename={project._id}-datacite.xml'
        assert resp.unicode_body == BASIC_DATACITE_XML.format(**format_kwargs)

        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-json', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/json'
        assert resp.content_disposition == f'attachment; filename={project._id}-datacite.json'
        assert resp.unicode_body == BASIC_DATACITE_JSON.format(**format_kwargs)

        metadata_record = GuidMetadataRecord.objects.for_guid(project._id)
        metadata_record.update({
            'language': 'en',
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

        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-xml', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/xml'
        assert resp.content_disposition == f'attachment; filename={project._id}-datacite.xml'
        assert resp.unicode_body == COMPLICATED_DATACITE_XML.format(**format_kwargs)

        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-json', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/json'
        assert resp.content_disposition == f'attachment; filename={project._id}-datacite.json'
        assert resp.unicode_body == COMPLICATED_DATACITE_JSON.format(**format_kwargs)

        ### now check that file
        format_kwargs['file_created_year'] = file.created.year
        resp = self.app.get(f'/{file_guid}/metadata/?format=turtle', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'text/turtle'
        assert resp.content_disposition == f'attachment; filename={file_guid}-metadata.ttl'
        assert resp.unicode_body == FILE_TURTLE.format(**format_kwargs)

        resp = self.app.get(f'/{file_guid}/metadata/?format=datacite-xml', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/xml'
        assert resp.content_disposition == f'attachment; filename={file_guid}-datacite.xml'
        assert resp.unicode_body == FILE_DATACITE_XML.format(**format_kwargs)

        resp = self.app.get(f'/{file_guid}/metadata/?format=datacite-json', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'application/json'
        assert resp.content_disposition == f'attachment; filename={file_guid}-datacite.json'
        assert resp.unicode_body == FILE_DATACITE_JSON.format(**format_kwargs)


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
    dcterms:publisher <http://localhost:5000> ;
    dcterms:rights [ foaf:name "No license" ] ;
    dcterms:rightsHolder "Me",
        "You" ;
    dcterms:title "this is a project title!" ;
    owl:sameAs <https://doi.org/10.70102/FK2osf.io/{project_id}> .

<http://localhost:5000/{user_id}> a osf:Agent ;
    dcterms:identifier "http://localhost:5000/{user_id}" ;
    dcterms:type foaf:Person ;
    foaf:name "Person McNamington" .

<http://localhost:5000> a osf:Agent ;
    dcterms:identifier "http://localhost:5000" ;
    dcterms:type foaf:Organization ;
    foaf:name "OSF" .'''


BASIC_DATACITE_XML = '''<?xml version='1.0' encoding='utf-8'?>
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.4/metadata.xsd">
  <identifier identifierType="DOI">10.70102/FK2osf.io/{project_id}</identifier>
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
  <publicationYear>{license_year}</publicationYear>
  <subjects/>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Center for Open Science</contributorName>
      <nameIdentifier nameIdentifierScheme="ROR">https://ror.org/05d5mza29</nameIdentifier>
      <nameIdentifier nameIdentifierScheme="URL">https://cos.io/</nameIdentifier>
    </contributor>
  </contributors>
  <dates>
    <date dateType="Created">{date}</date>
    <date dateType="Updated">{date}</date>
  </dates>
  <resourceType resourceTypeGeneral="Text">Project</resourceType>
  <alternateIdentifiers>
    <alternateIdentifier alternateIdentifierType="URL">http://localhost:5000/{project_id}</alternateIdentifier>
  </alternateIdentifiers>
  <rightsList>
    <rights>No license</rights>
  </rightsList>
  <descriptions>
    <description descriptionType="Abstract">this is a project description!</description>
  </descriptions>
  <fundingReferences/>
  <relatedIdentifiers/>
  <relatedItems/>
</resource>
'''


# doubled {{}} cleaned by (and necessary for) a call to str.format
BASIC_DATACITE_JSON = '''{{
  "alternateIdentifiers": [
    {{
      "alternateIdentifier": "http://localhost:5000/{project_id}",
      "alternateIdentifierType": "URL"
    }}
  ],
  "contributors": [
    {{
      "contributorName": {{
        "contributorName": "Center for Open Science",
        "nameType": "Organizational"
      }},
      "contributorType": "HostingInstitution",
      "nameIdentifier": {{
        "nameIdentifier": "https://cos.io/",
        "nameIdentifierScheme": "URL"
      }}
    }}
  ],
  "creators": [
    {{
      "creatorName": {{
        "creatorName": "Person McNamington",
        "nameType": "Personal"
      }},
      "nameIdentifier": {{
        "nameIdentifier": "http://localhost:5000/{user_id}",
        "nameIdentifierScheme": "URL"
      }}
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
  "identifier": {{
    "identifier": "10.70102/FK2osf.io/{project_id}",
    "identifierType": "DOI"
  }},
  "publicationYear": "{license_year}",
  "publisher": "OSF",
  "relatedIdentifiers": [],
  "relatedItems": [],
  "resourceType": {{
    "resourceType": "Project",
    "resourceTypeGeneral": "Text"
  }},
  "rightsList": [
    {{
      "rights": "No license"
    }}
  ],
  "subjects": [],
  "titles": [
    {{
      "title": "this is a project title!"
    }}
  ]
}}'''


COMPLICATED_TURTLE = '''@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://localhost:5000/{project_id}> a osf:Project ;
    dcterms:created "{date}" ;
    dcterms:creator <http://localhost:5000/{user_id}> ;
    dcterms:dateCopyrighted "2250-2254" ;
    dcterms:description "this is a project description!"@en ;
    dcterms:identifier "http://localhost:5000/{project_id}",
        "https://doi.org/10.70102/FK2osf.io/{project_id}" ;
    dcterms:language "en" ;
    dcterms:modified "{date}" ;
    dcterms:publisher <http://localhost:5000> ;
    dcterms:rights <https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode> ;
    dcterms:rightsHolder "Me",
        "You" ;
    dcterms:title "this is a project title!"@en ;
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

<https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode> dcterms:identifier "https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode" ;
    foaf:name "CC-By Attribution-NonCommercial-NoDerivatives 4.0 International" .

<http://localhost:5000/{user_id}> a osf:Agent ;
    dcterms:identifier "http://localhost:5000/{user_id}" ;
    dcterms:type foaf:Person ;
    foaf:name "Person McNamington" .

<http://localhost:5000> a osf:Agent ;
    dcterms:identifier "http://localhost:5000" ;
    dcterms:type foaf:Organization ;
    foaf:name "OSF" .'''


COMPLICATED_DATACITE_XML = '''<?xml version='1.0' encoding='utf-8'?>
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.4/metadata.xsd">
  <identifier identifierType="DOI">10.70102/FK2osf.io/{project_id}</identifier>
  <creators>
    <creator>
      <creatorName nameType="Personal">Person McNamington</creatorName>
      <nameIdentifier nameIdentifierScheme="URL">http://localhost:5000/{user_id}</nameIdentifier>
    </creator>
  </creators>
  <titles>
    <title xml:lang="en">this is a project title!</title>
  </titles>
  <publisher>OSF</publisher>
  <publicationYear>{project_created_year}</publicationYear>
  <subjects/>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Center for Open Science</contributorName>
      <nameIdentifier nameIdentifierScheme="ROR">https://ror.org/05d5mza29</nameIdentifier>
      <nameIdentifier nameIdentifierScheme="URL">https://cos.io/</nameIdentifier>
    </contributor>
  </contributors>
  <dates>
    <date dateType="Created">{date}</date>
    <date dateType="Updated">{date}</date>
  </dates>
  <language>en</language>
  <resourceType resourceTypeGeneral="Dataset">Project</resourceType>
  <alternateIdentifiers>
    <alternateIdentifier alternateIdentifierType="URL">http://localhost:5000/{project_id}</alternateIdentifier>
  </alternateIdentifiers>
  <rightsList>
    <rights rightsURI="https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode">CC-By Attribution-NonCommercial-NoDerivatives 4.0 International</rights>
  </rightsList>
  <descriptions>
    <description descriptionType="Abstract" xml:lang="en">this is a project description!</description>
  </descriptions>
  <fundingReferences>
    <fundingReference>
      <funderName>Mx. Moneypockets</funderName>
      <funderIdentifier funderIdentifierType="Crossref Funder ID">https://doi.org/10.$$$$</funderIdentifier>
      <awardNumber awardURI="https://moneypockets.example/millions">10000000</awardNumber>
      <awardTitle>because reasons</awardTitle>
    </fundingReference>
  </fundingReferences>
  <relatedIdentifiers/>
  <relatedItems/>
</resource>
'''


COMPLICATED_DATACITE_JSON = '''{{
  "alternateIdentifiers": [
    {{
      "alternateIdentifier": "http://localhost:5000/{project_id}",
      "alternateIdentifierType": "URL"
    }}
  ],
  "contributors": [
    {{
      "contributorName": {{
        "contributorName": "Center for Open Science",
        "nameType": "Organizational"
      }},
      "contributorType": "HostingInstitution",
      "nameIdentifier": {{
        "nameIdentifier": "https://cos.io/",
        "nameIdentifierScheme": "URL"
      }}
    }}
  ],
  "creators": [
    {{
      "creatorName": {{
        "creatorName": "Person McNamington",
        "nameType": "Personal"
      }},
      "nameIdentifier": {{
        "nameIdentifier": "http://localhost:5000/{user_id}",
        "nameIdentifierScheme": "URL"
      }}
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
      "descriptionType": "Abstract",
      "lang": "en"
    }}
  ],
  "fundingReferences": [
    {{
      "awardNumber": {{
        "awardNumber": "10000000",
        "awardURI": "https://moneypockets.example/millions"
      }},
      "awardTitle": "because reasons",
      "funderIdentifier": {{
        "funderIdentifier": "https://doi.org/10.$$$$",
        "funderIdentifierType": "Crossref Funder ID"
      }},
      "funderName": "Mx. Moneypockets"
    }}
  ],
  "identifier": {{
    "identifier": "10.70102/FK2osf.io/{project_id}",
    "identifierType": "DOI"
  }},
  "language": "en",
  "publicationYear": "{project_created_year}",
  "publisher": "OSF",
  "relatedIdentifiers": [],
  "relatedItems": [],
  "resourceType": {{
    "resourceType": "Project",
    "resourceTypeGeneral": "Dataset"
  }},
  "rightsList": [
    {{
      "rights": "CC-By Attribution-NonCommercial-NoDerivatives 4.0 International",
      "rightsURI": "https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode"
    }}
  ],
  "subjects": [],
  "titles": [
    {{
      "lang": "en",
      "title": "this is a project title!"
    }}
  ]
}}'''


FILE_TURTLE = '''@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://localhost:5000/{file_id}> a osf:File ;
    dcterms:created "{date}" ;
    dcterms:identifier "http://localhost:5000/{file_id}" ;
    dcterms:modified "{date}" ;
    osf:fileName "my-file.blarg" ;
    osf:filePath "/my-file.blarg" ;
    osf:hasFileVersion <http://localhost:8000/v2/files/{raw_file_id}/versions/1/> ;
    osf:isContainedBy <http://localhost:5000/{project_id}> .

<http://localhost:5000/{project_id}> a osf:Project ;
    dcterms:created "{date}" ;
    dcterms:creator <http://localhost:5000/{user_id}> ;
    dcterms:identifier "http://localhost:5000/{project_id}",
        "https://doi.org/10.70102/FK2osf.io/{project_id}" ;
    dcterms:publisher <http://localhost:5000> ;
    dcterms:title "this is a project title!"@en ;
    dcterms:type "Dataset" ;
    owl:sameAs <https://doi.org/10.70102/FK2osf.io/{project_id}> .

<http://localhost:8000/v2/files/{raw_file_id}/versions/1/> a osf:FileVersion ;
    dcterms:created "{date}" ;
    dcterms:creator <http://localhost:5000/{user_id}> ;
    dcterms:extent "0.000007 MB" ;
    dcterms:format "img/png" ;
    dcterms:modified "{date}" ;
    dcterms:requires <urn:checksum:sha-256::6ac3c336e4094835293a3fed8a4b5fedde1b5e2626d9838fed50693bba00af0e> ;
    osf:versionNumber "1" .

<http://localhost:5000/{user_id}> a osf:Agent ;
    dcterms:identifier "http://localhost:5000/{user_id}" ;
    dcterms:type foaf:Person ;
    foaf:name "Person McNamington" .

<http://localhost:5000> a osf:Agent ;
    dcterms:identifier "http://localhost:5000" ;
    dcterms:type foaf:Organization ;
    foaf:name "OSF" .'''


FILE_DATACITE_XML = '''<?xml version='1.0' encoding='utf-8'?>
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.4/metadata.xsd">
  <identifier identifierType="URL">http://localhost:5000/{file_id}</identifier>
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
  <publicationYear>{project_created_year}</publicationYear>
  <subjects/>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Center for Open Science</contributorName>
      <nameIdentifier nameIdentifierScheme="ROR">https://ror.org/05d5mza29</nameIdentifier>
      <nameIdentifier nameIdentifierScheme="URL">https://cos.io/</nameIdentifier>
    </contributor>
  </contributors>
  <dates>
    <date dateType="Created">{date}</date>
    <date dateType="Updated">{date}</date>
  </dates>
  <resourceType resourceTypeGeneral="Text">File</resourceType>
  <alternateIdentifiers>
    <alternateIdentifier alternateIdentifierType="URL">http://localhost:5000/{file_id}</alternateIdentifier>
  </alternateIdentifiers>
  <rightsList/>
  <descriptions/>
  <fundingReferences/>
  <relatedIdentifiers>
    <relatedIdentifier relatedIdentifierType="DOI" relationType="IsPartOf">10.70102/FK2osf.io/{project_id}</relatedIdentifier>
  </relatedIdentifiers>
  <relatedItems>
    <relatedItem relationType="IsPartOf" relatedItemType="Dataset">
      <relatedItemIdentifier relatedItemIdentifierType="DOI">10.70102/FK2osf.io/{project_id}</relatedItemIdentifier>
      <titles>
        <title xml:lang="en">this is a project title!</title>
      </titles>
      <publicationYear>{project_created_year}</publicationYear>
      <publisher>OSF</publisher>
    </relatedItem>
  </relatedItems>
</resource>
'''


FILE_DATACITE_JSON = '''{{
  "alternateIdentifiers": [
    {{
      "alternateIdentifier": "http://localhost:5000/{file_id}",
      "alternateIdentifierType": "URL"
    }}
  ],
  "contributors": [
    {{
      "contributorName": {{
        "contributorName": "Center for Open Science",
        "nameType": "Organizational"
      }},
      "contributorType": "HostingInstitution",
      "nameIdentifier": {{
        "nameIdentifier": "https://cos.io/",
        "nameIdentifierScheme": "URL"
      }}
    }}
  ],
  "creators": [
    {{
      "creatorName": {{
        "creatorName": "Person McNamington",
        "nameType": "Personal"
      }},
      "nameIdentifier": {{
        "nameIdentifier": "http://localhost:5000/{user_id}",
        "nameIdentifierScheme": "URL"
      }}
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
  "identifier": {{
    "identifier": "http://localhost:5000/{file_id}",
    "identifierType": "URL"
  }},
  "publicationYear": "{project_created_year}",
  "publisher": "OSF",
  "relatedIdentifiers": [
    {{
      "relatedIdentifier": "10.70102/FK2osf.io/{project_id}",
      "relatedIdentifierType": "DOI",
      "relationType": "IsPartOf"
    }}
  ],
  "relatedItems": [
    {{
      "publicationYear": "2023",
      "publisher": "OSF",
      "relatedItemIdentifier": {{
        "relatedItemIdentifier": "10.70102/FK2osf.io/{project_id}",
        "relatedItemIdentifierType": "DOI"
      }},
      "relatedItemType": "Dataset",
      "relationType": "IsPartOf",
      "titles": [
        {{
          "lang": "en",
          "title": "this is a project title!"
        }}
      ]
    }}
  ],
  "resourceType": {{
    "resourceType": "File",
    "resourceTypeGeneral": "Text"
  }},
  "rightsList": [],
  "subjects": [],
  "titles": [
    {{
      "title": "my-file.blarg"
    }}
  ]
}}'''
