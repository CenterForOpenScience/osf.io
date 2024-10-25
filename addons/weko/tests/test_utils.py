# -*- coding: utf-8 -*-
import json
import logging

from nose.tools import *  # noqa

from tests.base import OsfTestCase

from addons.weko.utils import validate_mapping


logger = logging.getLogger(__name__)


class TestWEKOUtils(OsfTestCase):

    def test_validate_success(self):
        d = r'''
{
    "@metadata": {
        "itemtype": {
            "name": "デフォルトアイテムタイプ（フル）(15)",
            "schema": "https://localhost:8443/items/jsonschema/15"
        }
    },
    "funder": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186901218[FUNDING]": {
            "subitem_1522399143519": {
                "subitem_1522399281603": "Other",
                "subitem_1522399333375": "{{value}}"
            }
        }
    },
    "funding-stream-code": {
        "@type": "string",
        "@createIf": "{{value}}"
    },
    "program-name-ja": {
        "@type": "string",
        "@createIf": "{{value}}"
    },
    "program-name-en": {
        "@type": "string",
        "@createIf": "{{value}}"
    },
    "japan-grant-number": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186901218[FUNDING]": {
            "subitem_1522399571623": {
                "subitem_1522399628911": "{{value}}"
            }
        }
    },
    "project-name-ja": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186901218[FUNDING]": {
            "subitem_1522399651758[]": {
                "subitem_1522721910626": "ja",
                "subitem_1522721929892": "{{value}}"
            }
        }
    },
    "project-name-en": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186901218[FUNDING]": {
            "subitem_1522399651758[]": {
                "subitem_1522721910626": "en",
                "subitem_1522721929892": "{{value}}"
            }
        }
    },
    "project-research-field": null,
    "grdm-files": null,
    "grdm-file:data-number": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617353299429[]": {
            "subitem_rights": "isIdenticalTo",
            "subitem_1522306287251": {
                "subitem_1522306382014": "Local",
                "subitem_1522306436033": "{{value}}"
            }
        }
    },
    "grdm-file:title-ja": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186331708[]": {
            "subitem_title": "{{value}}",
            "subitem_title_language": "ja"
        }
    },
    "grdm-file:title-en": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186331708[]": {
            "subitem_title": "{{value}}",
            "subitem_title_language": "en"
        }
    },
    "grdm-file:date-issued-updated": null,
    "grdm-file:data-description-ja": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186626617[]": {
            "subitem_description_type": "Other",
            "subitem_description": "{{value}}",
            "subitem_description_language": "ja"
        }
    },
    "grdm-file:data-description-en": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186626617[]": {
            "subitem_description_type": "Other",
            "subitem_description": "{{value}}",
            "subitem_description_language": "en"
        }
    },
    "grdm-file:data-research-field": {
        "@type": "string",
        "@createIf": "{{grdm_file_data_research_field_value}}{{project_research_field_value}}",
        "metadata.item_1617186609386[RESEARCH_FIELD_JA]": {
            "subitem_subject_scheme": "Other",
            "subitem_subject": "{% if grdm_file_data_research_field_value != \"project\" %}{{grdm_file_data_research_field_tooltip_0}}{% else %}{{project_research_field_tooltip_0}}{% endif %}",
            "subitem_subject_language": "ja"
        },
        "metadata.item_1617186609386[RESEARCH_FIELD_EN]": {
            "subitem_subject_scheme": "Other",
            "subitem_subject": "{% if grdm_file_data_research_field_value != \"project\" %}{{grdm_file_data_research_field_tooltip_1}}{% else %}{{project_research_field_tooltip_1}}{% endif %}",
            "subitem_subject_language": "en"
        }
    },
    "grdm-file:data-type": {
        "@type": "string",
        "@createIf": "{% if context == \"file\" %}{{value}}{% endif %}",
        "metadata.item_1617258105262": {
            "resourcetype": "{{value}}"
        }
    },
    "grdm-file:file-size": {
        "@type": "string",
        "@createIf": "{{value}}"
    },
    "grdm-file:data-policy-free": null,
    "grdm-file:data-policy-license": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186499011[]": [
            {
                "subitem_rights": "{{tooltip_0}} ({{grdm_file_data_policy_cite_ja_value}}) ({{grdm_file_data_policy_free_tooltip_0}})",
                "subitem_rights": "ja"
            },
            {
                "subitem_rights": "{{tooltip_1}} ({{grdm_file_data_policy_cite_en_value}}) ({{grdm_file_data_policy_free_tooltip_1}})",
                "subitem_rights": "en"
            }
        ]
    },
    "grdm-file:data-policy-cite-ja": null,
    "grdm-file:data-policy-cite-en": null,
    "grdm-file:access-rights": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186476635": {
            "subitem_access_right": "{{value}}"
        }
    },
    "grdm-file:available-date": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186660861[]": {
            "subitem_1522300695726": "Available",
            "subitem_1522300722591": "{{value}}"
        }
    },
    "grdm-file:repo-information-ja": null,
    "grdm-file:repo-information-en": null,
    "grdm-file:repo-url-doi-link": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186783814[]": {
            "subitem_identifier_uri": "{{value}}",
            "subitem_identifier_type": "URI"
        }
    },
    "grdm-file:creators": {
        "@type": "jsonarray",
        "metadata.item_1617186419668[]": {
            "nameIdentifiers[]": {
                "@createIf": "{{object_number}}",
                "nameIdentifierURI": "{{object_number}}",
                "nameIdentifierScheme": "e-Rad_Researcher"
            },
            "creatorNames[]": [
                {
                    "@createIf": "{{object_name_ja}}",
                    "creatorName": "{{object_name_ja}}",
                    "creatorNameLang": "ja"
                },
                {
                    "@createIf": "{{object_name_en}}",
                    "creatorName": "{{object_name_en}}",
                    "creatorNameLang": "en"
                }
            ]
        }
    },
    "grdm-file:hosting-inst-ja": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617349709064[HOSTING_INSTITUTION]": {
            "contributorType": "HostingInstitution",
            "contributorNames[]": {
                "contributorName": "{{value}}",
                "lang": "ja"
            }
        }
    },
    "grdm-file:hosting-inst-en": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617349709064[HOSTING_INSTITUTION]": {
            "contributorType": "HostingInstitution",
            "contributorNames[]": {
                "contributorName": "{{value}}",
                "lang": "en"
            }
        }
    },
    "grdm-file:hosting-inst-id": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617349709064[HOSTING_INSTITUTION]": {
            "contributorType": "HostingInstitution",
            "nameIdentifiers[]": {
                "nameIdentifierURI": "{{value}}",
                "nameIdentifierScheme": "ROR"
            }
        }
    },
    "grdm-file:data-man-number": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617349709064[DATA_MANAGER]": {
            "contributorType": "DataManager",
            "nameIdentifiers[]": {
                "nameIdentifierURI": "{{value}}",
                "nameIdentifierScheme": "e-Rad_Researcher"
            }
        }
    },
    "grdm-file:data-man-name-ja": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617349709064[DATA_MANAGER]": {
            "contributorType": "DataManager",
            "contributorNames[]": {
                "contributorName": "{{value}}",
                "lang": "ja"
            }
        }
    },
    "grdm-file:data-man-name-en": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617349709064[DATA_MANAGER]": {
            "contributorType": "DataManager",
            "contributorNames[]": {
                "contributorName": "{{value}}",
                "lang": "en"
            }
        }
    },
    "grdm-file:data-man-org-ja grdm-file:data-man-address-ja grdm-file:data-man-tel grdm-file:data-man-email": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617349709064[CONTACT_PERSON]": {
            "contributorType": "ContactPerson",
            "contributorNames[CONTACT_PERSON_JA]": {
                "contributorName": "{{grdm_file_data_man_org_ja_value}} {{grdm_file_data_man_address_ja_value}} {{grdm_file_data_man_tel_value}} {{grdm_file_data_man_email_value}}",
                "lang": "ja"
            }
        }
    },
    "grdm-file:data-man-org-en grdm-file:data-man-address-en": {
        "@type": "string",
        "@createIf": "{{value}}",
        "matadata.item_1617349709064[CONTACT_PERSON]": {
            "contributorType": "ContactPerson",
            "contributorNames[CONTACT_PERSON_EN]": {
                "contributorName": "{{grdm_file_data_man_org_en_value}} {{grdm_file_data_man_address_en_value}}",
                "lang": "en"
            }
        }
    },
    "grdm-file:remarks-ja": null,
    "grdm-file:remarks-en": null,
    "grdm-file:metadata-access-rights": null,
    "_": {
        "metadata.pubdate": "{{nowdate}}"
    }
}'''
        validate_mapping(json.loads(d.strip()))

    def test_validate_failure(self):
        d = r'''
{
    "@metadata": {
        "itemtype": {
            "name": "デフォルトアイテムタイプ（フル）(15)",
            "schema": "https://localhost:8443/items/jsonschema/15"
        }
    },
    "funder": {
        "@type": "string",
        "@skipIf": "{{value}}",
        "metadata.item_1617186901218[FUNDING]": {
            "subitem_1522399143519": {
                "subitem_1522399281603": "Other",
                "subitem_1522399333375": "{{value}}"
            }
        }
    },
    "_": {
        "metadata.pubdate": "{{nowdate}}"
    }
}'''
        with assert_raises(ValueError):
            validate_mapping(json.loads(d.strip()))

        d = r'''
{
    "@metadata": {
        "itemtype": {
            "name": "デフォルトアイテムタイプ（フル）(15)",
            "schema": "https://localhost:8443/items/jsonschema/15"
        }
    },
    "funder": {
        "@type": "string",
        "@createIf": "{{value}}",
        "metadata.item_1617186901218[FUNDING FAIL]": {
            "subitem_1522399143519": {
                "subitem_1522399281603": "Other",
                "subitem_1522399333375": "{{value}}"
            }
        }
    },
    "_": {
        "@type": "string",
        "metadata.pubdate": "{{nowdate}}"
    }
}'''
        with assert_raises(ValueError):
            validate_mapping(json.loads(d.strip()))