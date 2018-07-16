# -*- coding: utf-8 -*-

def get_user_social_jsonschema():
    return {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        '$id': '/social_fields',
        'title': 'Social Fields',
        'description': 'Social fields for the user serializer',
        'type': 'object',
        'properties': {
            'researcherId': {
                'description': 'The researcherId for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'baiduScholar': {
                'description': 'The baiduScholar for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'twitter': {
                'description': 'The twitter for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'ssrn': {
                'description': 'The ssrn for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'impactStory': {
                'description': 'The impactStory for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'researchGate': {
                'description': 'The researchGate for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'github': {
                'description': 'The github for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'scholar': {
                'description': 'The scholar for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'profileWebsites': {
                'description': 'The profileWebsites for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
            },
            'linkedIn': {
                'description': 'The linkedIn for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'academiaProfileID': {
                'description': 'The academiaProfileID for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },
            'orcid': {
                'description': 'The orcid for the given user',
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'maxItems': 1
            },

        }
    }
