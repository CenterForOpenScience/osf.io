from osf.utils.workflows import CollectionSubmissionStates

regex_or = "^" + ("|^").join(
    [state.db_name for state in CollectionSubmissionStates]
)

""" Payload for creating a schema response """
create_collection_action_payload = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "data": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "patterns": "collection-submission-actions",
                },
                "relationships": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "object",
                            "properties": {
                                "data": {
                                    "type": "object",
                                    "properties": {
                                        "id": {
                                            "pattern": "^[a-z0-9]{5,}",
                                        },
                                        "type": {
                                            "pattern": "collection-submission",
                                        },
                                        "trigger": {
                                            "pattern": regex_or,
                                        },
                                    },
                                    "required": [
                                        "id",
                                        "type",
                                    ],
                                },
                            },
                            "required": [
                                "data",
                            ],
                        },
                    },
                    "required": [
                        "target",
                    ],
                },
            },
            "required": [
                "type",
                "relationships",
            ],
        },
    },
    "required": [
        "data",
    ],
}
