from osf.models import GuidMetadataRecord
from api_tests.utils import create_test_file
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
        )
        # registration = factories.RegistrationFactory(project=project)
        # file = create_test_file(project, user)

        # unauthed, private project
        resp = self.app.get(f'/{project._id}/metadata/?format=datacite-json')
        assert resp.status_code == 302

        today = project.created.date()
        format_kwargs = {
            'project_id': project._id,
            'user_id': user._id,
            'date': str(today),
            'year': str(today.year),
        }

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

        resp = self.app.get(f'/{project._id}/metadata/?format=turtle', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'text/turtle'
        assert resp.content_disposition == f'attachment; filename={project._id}-metadata.ttl'
        assert resp.unicode_body == BASIC_TURTLE.format(**format_kwargs)

        metadata_record = GuidMetadataRecord.objects.for_guid(project._id)
        metadata_record.update({
            'language': 'es',
            'resource_type_general': 'Book',
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

        resp = self.app.get(f'/{project._id}/metadata/?format=turtle', auth=user.auth)
        assert resp.status_code == 200
        assert resp.content_type == 'text/turtle'
        assert resp.content_disposition == f'attachment; filename={project._id}-metadata.ttl'
        assert resp.unicode_body == COMPLICATED_TURTLE.format(**format_kwargs)


# doubled {{}} cleaned by a call to .format()
BASIC_DATACITE_JSON = '''{{
  "identifiers": [
    {{
      "identifier": "10.70102/FK2osf.io/{project_id}",
      "identifierType": "DOI"
    }}
  ],
  "creators": [
    {{
      "nameIdentifiers": [
        {{
          "nameIdentifier": "http://localhost:5000/{user_id}/",
          "nameIdentifierScheme": "URL"
        }}
      ],
      "nameType": "Personal",
      "creatorName": "Person McNamington",
      "familyName": "McNamington",
      "givenName": "Person",
      "name": "Person McNamington"
    }}
  ],
  "contributors": [
    {{
      "nameType": "Organizational",
      "contributorType": "HostingInstitution",
      "contributorName": "Open Science Framework",
      "name": "Open Science Framework",
      "nameIdentifiers": [
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://ror.org/05d5mza29/",
          "nameIdentifierScheme": "ROR"
        }},
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://grid.ac/institutes/grid.466501.0/",
          "nameIdentifierScheme": "GRID"
        }}
      ]
    }}
  ],
  "titles": [
    {{
      "title": "this is a project title!"
    }}
  ],
  "publisher": "Open Science Framework",
  "publicationYear": "{year}",
  "types": {{
    "resourceType": "Project",
    "resourceTypeGeneral": "Text"
  }},
  "schemaVersion": "http://datacite.org/schema/kernel-4",
  "dates": [
    {{
      "date": "{date}",
      "dateType": "Created"
    }},
    {{
      "date": "{date}",
      "dateType": "Updated"
    }},
    {{
      "date": "{date}",
      "dateType": "Issued"
    }}
  ],
  "descriptions": [
    {{
      "descriptionType": "Abstract",
      "description": "this is a project description!"
    }}
  ],
  "subjects": []
}}'''


BASIC_DATACITE_XML = '''<?xml version='1.0' encoding='utf-8'?>
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.3/metadata.xsd">
  <identifier identifierType="DOI">10.70102/FK2osf.io/{project_id}</identifier>
  <creators>
    <creator>
      <creatorName nameType="Personal">Person McNamington</creatorName>
      <givenName>Person</givenName>
      <familyName>McNamington</familyName>
      <nameIdentifier nameIdentifierScheme="URL">http://localhost:5000/{user_id}/</nameIdentifier>
    </creator>
  </creators>
  <titles>
    <title>this is a project title!</title>
  </titles>
  <publisher>Open Science Framework</publisher>
  <publicationYear>{year}</publicationYear>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Open Science Framework</contributorName>
      <nameIdentifier nameIdentifierScheme="ROR">https://ror.org/05d5mza29/</nameIdentifier>
      <nameIdentifier nameIdentifierScheme="GRID">https://grid.ac/institutes/grid.466501.0/</nameIdentifier>
    </contributor>
  </contributors>
  <dates>
    <date dateType="Created">{date}</date>
    <date dateType="Updated">{date}</date>
    <date dateType="Issued">{date}</date>
  </dates>
  <resourceType resourceTypeGeneral="Text">Project</resourceType>
  <descriptions>
    <description descriptionType="Abstract">this is a project description!</description>
  </descriptions>
</resource>
'''

BASIC_TURTLE = '''@prefix dct: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix osf: <https://osf.io/vocab/2022/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://localhost:5000/{project_id}> a osf:Node ;
    dct:available false ;
    dct:created "{date}" ;
    dct:creator <http://localhost:5000/{user_id}> ;
    dct:description "this is a project description!" ;
    dct:identifier "http://localhost:5000/{project_id}" ;
    dct:modified "{date}" ;
    dct:title "this is a project title!" ;
    dct:type osf:project .

<http://localhost:5000/{user_id}> a osf:OSFUser ;
    dct:created "{date}" ;
    dct:identifier "http://localhost:5000/{user_id}" ;
    dct:modified "{date}" ;
    foaf:name "Person McNamington" .

'''


COMPLICATED_DATACITE_JSON = '''{{
  "identifiers": [
    {{
      "identifier": "10.70102/FK2osf.io/{project_id}",
      "identifierType": "DOI"
    }}
  ],
  "creators": [
    {{
      "nameIdentifiers": [
        {{
          "nameIdentifier": "http://localhost:5000/{user_id}/",
          "nameIdentifierScheme": "URL"
        }}
      ],
      "nameType": "Personal",
      "creatorName": "Person McNamington",
      "familyName": "McNamington",
      "givenName": "Person",
      "name": "Person McNamington"
    }}
  ],
  "contributors": [
    {{
      "nameType": "Organizational",
      "contributorType": "HostingInstitution",
      "contributorName": "Open Science Framework",
      "name": "Open Science Framework",
      "nameIdentifiers": [
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://ror.org/05d5mza29/",
          "nameIdentifierScheme": "ROR"
        }},
        {{
          "name": "Open Science Framework",
          "nameIdentifier": "https://grid.ac/institutes/grid.466501.0/",
          "nameIdentifierScheme": "GRID"
        }}
      ]
    }}
  ],
  "titles": [
    {{
      "title": "this is a project title!"
    }}
  ],
  "publisher": "Open Science Framework",
  "publicationYear": "{year}",
  "types": {{
    "resourceType": "Book",
    "resourceTypeGeneral": "Other"
  }},
  "schemaVersion": "http://datacite.org/schema/kernel-4",
  "dates": [
    {{
      "date": "{date}",
      "dateType": "Created"
    }},
    {{
      "date": "{date}",
      "dateType": "Updated"
    }},
    {{
      "date": "{date}",
      "dateType": "Issued"
    }}
  ],
  "descriptions": [
    {{
      "descriptionType": "Abstract",
      "description": "this is a project description!"
    }}
  ],
  "subjects": [],
  "language": "es",
  "fundingReferences": [
    {{
      "funderName": "Mx. Moneypockets",
      "funderIdentifier": "https://doi.org/10.$$$$",
      "funderIdentifierType": "Crossref Funder ID",
      "awardNumber": "10000000",
      "awardURI": "https://moneypockets.example/millions",
      "awardTitle": "because reasons"
    }}
  ]
}}'''


COMPLICATED_DATACITE_XML = '''<?xml version='1.0' encoding='utf-8'?>
<resource xmlns="http://datacite.org/schema/kernel-4" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.3/metadata.xsd">
  <identifier identifierType="DOI">10.70102/FK2osf.io/{project_id}</identifier>
  <creators>
    <creator>
      <creatorName nameType="Personal">Person McNamington</creatorName>
      <givenName>Person</givenName>
      <familyName>McNamington</familyName>
      <nameIdentifier nameIdentifierScheme="URL">http://localhost:5000/{user_id}/</nameIdentifier>
    </creator>
  </creators>
  <titles>
    <title>this is a project title!</title>
  </titles>
  <publisher>Open Science Framework</publisher>
  <publicationYear>{year}</publicationYear>
  <contributors>
    <contributor contributorType="HostingInstitution">
      <contributorName nameType="Organizational">Open Science Framework</contributorName>
      <nameIdentifier nameIdentifierScheme="ROR">https://ror.org/05d5mza29/</nameIdentifier>
      <nameIdentifier nameIdentifierScheme="GRID">https://grid.ac/institutes/grid.466501.0/</nameIdentifier>
    </contributor>
  </contributors>
  <dates>
    <date dateType="Created">{date}</date>
    <date dateType="Updated">{date}</date>
    <date dateType="Issued">{date}</date>
  </dates>
  <language>es</language>
  <resourceType resourceTypeGeneral="Other">Book</resourceType>
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
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://localhost:5000/{project_id}> a osf:Node ;
    dct:available false ;
    dct:created "{date}" ;
    dct:creator <http://localhost:5000/{user_id}> ;
    dct:description "this is a project description!" ;
    dct:identifier "http://localhost:5000/{project_id}" ;
    dct:language "es" ;
    dct:modified "{date}" ;
    dct:title "this is a project title!" ;
    dct:type osf:project,
        "Book" ;
    osf:funder [ dct:identifier "https://doi.org/10.$$$$" ;
            foaf:name "Mx. Moneypockets" ;
            osf:award_number "10000000" ;
            osf:award_title "because reasons" ;
            osf:award_uri "https://moneypockets.example/millions" ] .

<http://localhost:5000/{user_id}> a osf:OSFUser ;
    dct:created "{date}" ;
    dct:identifier "http://localhost:5000/{user_id}" ;
    dct:modified "{date}" ;
    foaf:name "Person McNamington" .

'''
