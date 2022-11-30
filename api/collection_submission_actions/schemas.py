
""" Payload for creating a schema response """
create_collection_action_payload = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'type': 'object',
    'properties': {
        'data': {
            'type': 'object',
            'properties': {
                'type': {
                    'type': 'string',
                },
                'relationships': {
                    'type': 'object',
                    'properties': {
                        'target': {
                            'type': 'object',
                            'properties': {
                                'data': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {
                                            'pattern': '^[a-z0-9]{5,}',
                                        },
                                        'type': {
                                            'pattern': 'collection-submission',
                                        },
                                    },
                                    'required': [
                                        'id',
                                        'type',
                                    ],
                                },
                            },
                            'required': [
                                'data',
                            ],
                        },
                    },
                    'required': [
                        'target',
                    ],
                },
            },
            'required': [
                'type',
                'relationships',
            ],
        },
    },
    'required': [
        'data',
    ],
}
