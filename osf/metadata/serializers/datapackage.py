import json
from osf.metadata.serializers import _base
from osf.metadata.serializers.datacite import DataciteJsonMetadataSerializer

PROFILE_URL = "https://datapackage.org/profiles/2.0/datapackage.json"


class DatapackageSerializer(_base.MetadataSerializer):
    mediatype = "application/json"  # type: ignore

    def filename_for_itemid(self, itemid: str):
        return f"{itemid}.datapackage.json"

    def serialize(self) -> str:
        return json.dumps(
            self.metadata_as_dict(),
            indent=2,
            sort_keys=True,
        )

    # NOTE: this mapping can be done by `dplib-py` on Python3.8+
    def metadata_as_dict(self) -> dict:
        dataset = DataciteJsonMetadataSerializer(self.basket).metadata_as_dict()
        package = {"$schema": PROFILE_URL, "resources": []}

        # Id
        for identifier in dataset.get("identifiers", []):
            type = identifier.get("identifierType")
            value = identifier.get("identifier")
            if value and type == "DOI":
                package["id"] = value
                break

        # Title
        for title in dataset.get("titles", []):
            type = title.get("titleType")
            value = title.get("title")
            if value and not type:
                package["title"] = value
                break

        # Description
        for title in dataset.get("descriptions", []):
            type = title.get("descriptionType")
            value = title.get("description")
            if value and type == "Abstract":
                package["description"] = value
                break

        # Homepage
        for identifier in dataset.get("identifiers", []):
            type = identifier.get("identifierType")
            value = identifier.get("identifier")
            if value and type == "URL":
                package["homepage"] = value
                break

        # Version
        version = dataset.get("version")
        if version:
            package["version"] = version

        # Keywords
        for subject in dataset.get("subjects", []):
            value = subject.get("subject")
            if value:
                package.setdefault("keywords", []).append(value)

        # Licenses
        for right in dataset.get("rightsList", []):
            license = {}
            license["name"] = right.get("rightsIdentifier")
            license["path"] = right.get("rightsUri")
            license["title"] = right.get("rights")
            license = {k: v for k, v in license.items() if v is not None}
            if license:
                package.setdefault("licenses", []).append(license)

        # Contributors
        creators = dataset.get("creators", [])
        contributors = dataset.get("contributors", [])
        for type, items in [("creator", creators), (None, contributors)]:
            for item in items:
                type = item.get("contributorType", type)
                contributor = {}
                contributor["title"] = item.get("name")
                contributor["givenName"] = item.get("givenName")
                contributor["familyName"] = item.get("familyName")
                if type:
                    contributor["roles"] = [type]
                for affiliation in item.get("affiliations", []):
                    name = affiliation.get("name")
                    if name:
                        contributor["organization"] = name
                        break
                contributor = {k: v for k, v in contributor.items() if v is not None}
                if contributor:
                    package.setdefault("contributors", []).append(contributor)

        # Resources
        # TODO: is there a way to get actual file urls from the metadata?

        return package
