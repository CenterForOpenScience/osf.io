import pytest

from api.base.parsers import JSONAPIMultipleRelationshipsParser


SINGLE_RELATIONSHIP = {
    'region': {
        'data': {
            'type': 'regions',
            'id': 'us-1'
        }
    }
}

MULTIPLE_RELATIONSHIP = {
    'affiliated_institutions': {
        'data': [
            {
                'type': 'institutions',
                'id': 'cos'
            }, {
                'type': 'institutions',
                'id': 'ljaf'
            }
        ]
    }
}

MIXED_RELATIONSHIP = {
    'region': {
        'data': {
            'type': 'regions',
            'id': 'us-1'
        }
    },
    'affiliated_institutions': {
        'data': [
            {
                'type': 'institutions',
                'id': 'cos'
            }, {
                'type': 'institutions',
                'id': 'ljaf'
            }
        ]
    }
}

MULTIPLE_SINGLE_RELATIONSHIPS = {
    'node': {
        'data': {
            'type': 'nodes',
            'id': 'abcde'
        }
    },
    'provider': {
        'data': {
            'type': 'preprint_providers',
            'id': 'agrixiv'
        }
    }
}

MULTIPLE_MULTIPLE_RELATIONSHIPS = {
    'affiliated_institutions': {
        'data': [
            {
                'type': 'institutions',
                'id': 'cos'
            }, {
                'type': 'institutions',
                'id': 'ljaf'
            }
        ]
    },
    'providers': {
        'data': [
            {
                'type': 'preprint_providers',
                'id': 'agrixiv'
            }, {
                'type': 'preprint_providers',
                'id': 'osfpreprints'
            }
        ]
    }
}


class TestMultipleRelationshipsParser:

    @pytest.mark.parametrize('relationship,expected',
    [
        (SINGLE_RELATIONSHIP, {'region': 'us-1'}),
        (MULTIPLE_RELATIONSHIP, {'affiliated_institutions': ['cos', 'ljaf']}),
        (MIXED_RELATIONSHIP, {'region': 'us-1', 'affiliated_institutions': ['cos', 'ljaf']}),
        (MULTIPLE_SINGLE_RELATIONSHIPS, {'node': 'abcde', 'provider': 'agrixiv'}),
        (MULTIPLE_MULTIPLE_RELATIONSHIPS, {'affiliated_institutions': ['cos', 'ljaf'], 'providers': ['agrixiv', 'osfpreprints']}),
    ])
    def test_flatten_relationships(self, relationship, expected):
        parser = JSONAPIMultipleRelationshipsParser()
        assert JSONAPIMultipleRelationshipsParser.flatten_relationships(parser, relationship) == expected
