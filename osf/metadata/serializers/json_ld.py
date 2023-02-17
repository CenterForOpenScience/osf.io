from osf.metadata import gather
from osf.metadata.serializers import _base


class JsonLdMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/json-ld'

    def filename(self, osfguid: str):
        return f'{osfguid}-metadata.json-ld'

    def serialize(self, basket: gather.Basket):
        print(basket)
        print(basket.__dict__)
        return {
           "@context": "https://schema.org",
           "@type": "Dataset",
           "@id": format_id(basket),
           "dateCreated": "2020-04-06T16:16:20+00:00",
           "dateModified": "2020-04-06T16:16:24+00:00",
           "name": format_name(basket),
           "description": format_description(basket),
           "url": format_url(basket),
           "keywords":"Homo sapiens",
           "publisher":{
              "@type": "Organization",
              "name": "Center For Open Science"
           },
           "creator": format_creators(basket),
           "distribution": format_distibution(basket),
           "license": format_license(basket),
           "identifier":"https://doi.org/10.6084/m9.figshare.10266554.v2",
           "citation":"https://doi.org/10.1038/s41597-019-0303-3"
        }



def format_creators(self):
    return [
        {
            "@type": "Person",
            "name": "Metadata Creator"
        }
    ]


def format_distibution(self):
    return [
        {
            "@type": "DataDownload",
            "contentUrl": "https://figshare.com/ndownloader/files/22224060",
            "encodingFormat": "text/plain",
            "license": "https://creativecommons.org/publicdomain/zero/1.0/"
        }
    ]