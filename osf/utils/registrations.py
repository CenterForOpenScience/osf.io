from past.builtins import basestring
import copy
import re

from future.moves.urllib.parse import urljoin

from osf.exceptions import SchemaBlockConversionError
from website import settings


def strip_registered_meta_comments(messy_dict_or_list, in_place=False):
    """Removes Prereg Challenge comments from a given `registered_meta` dict.

    Nothing publicly exposed needs these comments:
    ```
    {
        "registered_meta": {
            "q20": {
                "comments": [ ... ], <~~~ THIS
                "value": "foo",
                "extra": []
            },
        }
    }
    ```

    If `in_place` is truthy, modifies `messy_dict_or_list` and returns it.
    Else, returns a deep copy without modifying the given `messy_dict_or_list`
    """
    obj = messy_dict_or_list if in_place else copy.deepcopy(messy_dict_or_list)

    if isinstance(obj, list):
        for nested_obj in obj:
            strip_registered_meta_comments(nested_obj, in_place=True)
    elif isinstance(obj, dict):
        comments = obj.get('comments', None)

        # some schemas have a question named "comments" -- those will have a dict value
        if isinstance(comments, list):
            del obj['comments']

        # dig into the deeply nested structure
        for nested_obj in obj.values():
            strip_registered_meta_comments(nested_obj, in_place=True)
    return obj


"""
Old workflow uses DraftRegistration.registration_metadata and Registration.registered_meta.
New workflow uses DraftRegistration.registration_responses and Registration.registration_responses.

Both workflows need to be accommodated for the foreseeable future, so writing to one field
needs to write to the other field.

Contains helps for "flatten_registration_metadata" for converting from old to new, and
"expand_registration_responses" for converting from new to old.
"""

# relative urls from the legacy 'nested' format
FILE_VIEW_URL_TEMPLATE = '/project/{node_id}/files/osfstorage/{file_id}'
FILE_VIEW_URL_REGEX = re.compile(r'/(?:project/)?(?P<node_id>\w{5})/files/osfstorage/(?P<file_id>\w{24})')

# use absolute URLs in new 'flattened' format
FILE_HTML_URL_TEMPLATE = urljoin(settings.DOMAIN, '/project/{node_id}/files/osfstorage/{file_id}')
FILE_DOWNLOAD_URL_TEMPLATE = urljoin(settings.DOMAIN, '/download/{file_id}')

def flatten_registration_metadata(schema, registered_meta):
    """
    Extracts questions/nested registration_responses - makes use of schema block `registration_response_key`
    and block_type to assemble flattened registration_responses.

    For example, if the registration_response_key = "description-methods.planned-sample.question7b",
    this will recurse through the registered_meta, looking for each key, starting with "description-methods",
    then "planned-sample", and finally "question7b", returning the most deeply nested value corresponding
    with the final key to flatten the dictionary.
    :schema, RegistrationSchema instance
    :registered_meta, dict containing the legacy "nested" registered_meta/registration_metadata
    :returns dictionary, registration_responses, flattened dictionary with registration_response_keys
    top-level
    """
    registration_responses = {}
    registration_response_keys = schema.schema_blocks.filter(
        registration_response_key__isnull=False
    ).values(
        'registration_response_key',
        'block_type'
    )

    for registration_response_key_dict in registration_response_keys:
        key = registration_response_key_dict['registration_response_key']
        registration_responses[key] = get_nested_answer(
            registered_meta,
            registration_response_key_dict['block_type'],
            key.split('.')
        )
    return registration_responses

# For flatten_registration_metadata
def build_file_ref(file):
    """
    Extracts name, file_id, and sha256 from the nested "extras" dictionary.
    Pulling name from selectedFileName and the file_id from the viewUrl.

    Some weird data here...such as {u'selectedFileName': u'No file selected'}
    Raises SchemaBlockConversionError if it's too weird to handle.

    :returns dictionary formatted as below
    {
        file_id: <file_id>,
        file_name: <file_name>,
        file_hashes: {
            sha256: <sha256>,
        },
        file_urls: {
            html: <url to webpage with/about file>,
            download: <url to download file directly>,
        },
    }
    """
    file_data = file.get('data')

    # on a Registration, viewUrl is the only place the file/node ids are accurate.
    # the others refer to the original file on the node, not the file that was archived on the reg
    view_url = file.get('viewUrl')
    file_id = None
    node_id = None
    if view_url:
        url_match = FILE_VIEW_URL_REGEX.search(view_url)
        if not url_match:
            raise SchemaBlockConversionError('Unexpected file viewUrl: {}'.format(view_url))
        groupdict = url_match.groupdict()
        file_id = groupdict['file_id']
        node_id = groupdict['node_id']
    elif file_data:
        # this data is bad and it should feel bad
        id_from_path = file_data.get('path', '').lstrip('/')
        file_id = id_from_path or file.get('fileId')
        node_id = file.get('nodeId')

    if not (file_id and node_id):
        raise SchemaBlockConversionError('Could not find file and node ids in file info: {}'.format(file))

    file_name = file.get('selectedFileName')
    if file_data and not file_name:
        file_name = file_data.get('name')

    sha256 = file.get('sha256')
    if file_data and not sha256:
        sha256 = file_data.get('extra', {}).get('hashes', {}).get('sha256')

    return {
        'file_id': file_id,
        'file_name': file_name,
        'file_hashes': {'sha256': sha256} if sha256 else {},
        'file_urls': {
            'html': FILE_HTML_URL_TEMPLATE.format(file_id=file_id, node_id=node_id),
            'download': FILE_DOWNLOAD_URL_TEMPLATE.format(file_id=file_id),
        },
    }

# For flatten_registration_metadata
def build_file_refs(messy_file_infos):
    for file_info in messy_file_infos:
        if not file_info:
            continue
        if len(file_info) == 1 and file_info.get('selectedFileName') == 'No file selected':
            continue
        yield build_file_ref(file_info)

# For flatten_registration_metadata
def get_value_or_extra(nested_response, block_type, key, keys):
    """
    Sometimes the relevant information is stored under "extra" for files,
    otherwise, "value".

    :params, nested dictionary
    :block_type, string, current block type
    :key, particular key in question
    :keys, array of keys remaining to recurse through to find the user's answer
    :returns array (files or multi-response answers) or a string IF deepest level of nesting,
    otherwise, returns a dictionary to get the next level of nesting.
    """
    keyed_value = nested_response.get(key, '')
    # No guarantee that the key exists in the dictionary
    if isinstance(keyed_value, basestring):
        return keyed_value

    # If we are on the most deeply nested key (no more keys left in array),
    # and the block type is "file-input", the information we want is
    # stored under extra
    if block_type == 'file-input' and not keys:
        extra = keyed_value.get('extra', [])
        extra_list = extra if isinstance(extra, list) else [extra]
        return list(build_file_refs(extra_list))

    value = keyed_value.get('value')
    if value is None:
        return ''
    if isinstance(value, bool):
        return str(value)
    return value

# For flatten_registration_metadata
def get_nested_answer(nested_response, block_type, keys):
    """
    Recursively fetches the nested response in registered_meta.

    :params nested_response dictionary
    :params keys array, of nested question_ids: ["recommended-analysis", "specify", "question11c"]
    :returns array (files or multi-response answers) or a string
    """
    if isinstance(nested_response, dict):
        if not keys:
            raise SchemaBlockConversionError('Unexpected nested object (expected list or string)', nested_response)
        key = keys.pop(0)
        # Returns the value associated with the given key
        value = get_value_or_extra(nested_response, block_type, key, keys)
        return get_nested_answer(value, block_type, keys)
    else:
        # Once we've drilled down through the entire dictionary, our nested_response
        # should be an array or a string
        if not isinstance(nested_response, (list, basestring)):
            raise SchemaBlockConversionError('Unexpected value type (expected list or string)', nested_response)
        return nested_response

def expand_registration_responses(schema, registration_responses, file_storage_resource):
    """
    Expanding `registration_responses` into Draft.registration_metadata or
    Registration.registered_meta. registration_responses are more flat;
    "registration_response_keys" are top level.  Registration_metadata/registered_meta
    will have a more deeply nested format.
    :returns registration_metadata, dictionary
    """
    registration_responses = copy.deepcopy(registration_responses)

    # Pull out all registration_response_keys and their block types
    registration_response_keys = schema.schema_blocks.filter(
        registration_response_key__isnull=False
    ).values(
        'registration_response_key',
        'block_type'
    )

    metadata = {}

    for registration_response_key_dict in registration_response_keys:
        response_key = str(registration_response_key_dict['registration_response_key'])
        # Turns "confirmatory-analyses-further.further.question2c" into
        # ['confirmatory-analyses-further', 'value', 'further', 'value', 'question2c']
        nested_keys = response_key.replace('.', '.value.').split('.')
        block_type = registration_response_key_dict['block_type']

        # Continues to add to metadata with every registration_response_key
        metadata = build_registration_metadata_dict(
            nested_keys,
            metadata=metadata,
            value=build_answer_block(
                block_type,
                registration_responses.get(response_key, ''),
                file_storage_resource=file_storage_resource
            )
        )
    return metadata

# For expanding registration_responses
def set_nested_values(nested_dictionary, keys, value):
    """
    Drills down through the nested dictionary, accessing each key in the array,
    and sets the last key equal to the passed in value, if this key doesn't already exist.

    Assumes all keys are present, except for potentially the final key.

    :param nested_dictionary, dictionary
    :param keys, array
    :param value, object, array, or string
    """
    for key in keys[:-1]:
        nested_dictionary = nested_dictionary.get(key, None)

    final_key = keys[-1]
    if not nested_dictionary.get(final_key):
        nested_dictionary[final_key] = value

# For expanding registration_responses
def build_extra_file_dict(file_ref):
    url_match = FILE_VIEW_URL_REGEX.search(file_ref['file_urls']['html'])
    if not url_match:
        raise SchemaBlockConversionError('Expected `file_urls.html` in format `/project/<node_id>/files/osfstorage/<file_id>`')

    groups = url_match.groupdict()
    node_id = groups['node_id']
    file_id = groups['file_id']

    file_name = file_ref['file_name']
    sha256 = file_ref['file_hashes']['sha256']

    # viewUrl, selectedFileName, and sha256 are everything needed for the return trip
    # (see `osf.utils.build_file_ref`)
    return {
        'viewUrl': FILE_VIEW_URL_TEMPLATE.format(node_id=node_id, file_id=file_id),
        'selectedFileName': file_name,
        'sha256': sha256,
        'nodeId': node_id,  # Used in _find_orphan_files
        'data': {
            'name': file_name,  # What legacy FE needs for rendering file on the draft
        }
    }

# For expanding registration_responses
def build_answer_block(block_type, value, file_storage_resource=None):
    extra = []
    if block_type == 'file-input':
        extra = list(map(build_extra_file_dict, value))
        value = ''
    return {
        'comments': [],
        'value': value,
        'extra': extra
    }

# For expanding registration_responses
def build_registration_metadata_dict(keys, current_index=0, metadata={}, value={}):
    """
    Function will recursively loop through each key in the list, checking if it exists in metadata, if not,
    adding another nested level in the dictionary.

    For example, calling build_registration_metadata_dict(
        ["recommended-analysis", "value", "specify", "value", "question11c"], value='hello'), yields,

    {
        'recommended-analysis': {
            'value': {
                'specify': {
                    'value': {
                        'question11c': 'hello'
                    }
                }
            }
        }
    }
    :param keys array, of nested question_ids: ["recommended-analysis", "value", "specify", "value", "question11c"]
    :param current_index, call initially with 0
    :param metadata - registration_metadata
    :param value, provide most deeply nested value.
    :returns partial registration_metadata
    """
    if current_index == len(keys):
        # We've iterated through all the keys, so we exit.
        return metadata
    else:
        # All keys from left to right including the current key.
        current_chain = keys[0:current_index + 1]
        # If we're on the final key, use the passed in value
        val = value if current_index == len(keys) - 1 else {}
        # set_nested_values incrementally adds another layer of nesting to the dictionary,
        # until we get to the deepest level where we can set the value equal to the user's response
        set_nested_values(metadata, current_chain, val)
        return build_registration_metadata_dict(keys, current_index + 1, metadata, value)
