""" Payload for creating a schema response """
create_schema_response_payload = {
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
                        'registration': {
                            'type': 'object',
                            'properties': {
                                'data': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {
                                            'pattern': '^[a-z0-9]{5,}',
                                        },
                                        'type': {
                                            'pattern': 'registrations',
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
                        'registration',
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
