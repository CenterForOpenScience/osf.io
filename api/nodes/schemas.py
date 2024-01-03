
""" Payload for creating a addon """
create_addon_payload = {
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
                        'provider': {
                            'type': 'object',
                            'properties': {
                                'data': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {
                                            'pattern': '[a-z0-9]',
                                        },
                                        'type': {
                                            'pattern': 'addons',
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
                        'provider',
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
