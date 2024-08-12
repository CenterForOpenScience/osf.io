DEFAULT_TEST_SCHEMA_NAME = "***OSF Internal Test Schema***"
TEST_SCHEMA_SINGLE_SELECT_OPTIONS = ["A", "B", "A and B", "None of the Above"]
TEST_SCHEME_MULTI_SELECT_OPTIONS = ["D", "E", "F", "G"]
DEFAULT_TEST_SCHEMA = {
    "name": DEFAULT_TEST_SCHEMA_NAME,
    "version": 1,
    "description": "Test Registration Schema for internal use only",
    "atomicSchema": True,
    "blocks": [
        {
            "block_type": "page-heading",
            "display_text": "Text Inputs",
        },
        {
            "block_type": "question-label",
            "display_text": "Short text input",
            "help_text": "This is meant for storing ~a single line of text",
        },
        {
            "block_type": "short-text-input",
            "registration_response_key": "q1",
            "required": True,
        },
        {
            "block_type": "question-label",
            "display_text": "Long text input",
            "help_text": "This is meant for storing a paragraph",
        },
        {
            "block_type": "long-text-input",
            "registration_response_key": "q2",
            "required": True,
        },
        {
            "block_type": "page-heading",
            "display_text": "Select Inputs",
        },
        {
            "block_type": "question-label",
            "display_text": "Single-select input",
            "help_text": "This allows the user to select one entry from a list of options",
        },
        {
            "block_type": "single-select-input",
            "registration_response_key": "q3",
            "required": True,
        },
        {
            "block_type": "select-input-option",
            "display_text": "A",
        },
        {
            "block_type": "select-input-option",
            "display_text": "B",
        },
        {
            "block_type": "select-input-option",
            "display_text": "A and B",
        },
        {
            "block_type": "select-input-option",
            "display_text": "None of the Above",
        },
        {
            "block_type": "question-label",
            "display_text": "Multi-select input",
            "help_text": "This allows the user to select several entires from a list of options",
        },
        {
            "block_type": "multi-select-input",
            "registration_response_key": "q4",
            "required": True,
        },
        {
            "block_type": "select-input-option",
            "display_text": "D",
        },
        {
            "block_type": "select-input-option",
            "display_text": "E",
        },
        {
            "block_type": "select-input-option",
            "display_text": "F",
        },
        {
            "block_type": "select-input-option",
            "display_text": "G",
        },
        {
            "block_type": "page-heading",
            "display_text": "OSF Inputs",
        },
        {
            "block_type": "question-label",
            "display_text": "Contributors input",
            "help_text": "This allows the user to specify one or more OSF Users",
        },
        {
            "block_type": "contributors-input",
            "registration_response_key": "q5",
            "required": False,
        },
        {
            "block_type": "question-label",
            "display_text": "File input",
            "help_text": "This allows the user to attach a file to answer the question.",
        },
        {
            "block_type": "file-input",
            "registration_response_key": "q6",
            "required": False,
        },
    ],
}
