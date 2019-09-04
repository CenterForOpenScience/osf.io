import copy


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

# For flatten_registration_metadata
def extract_file_info(file):
    """
    Extracts name and file_id from the nested "extras" dictionary.
    Pulling name from selectedFileName and the file_id from the viewUrl.

    Some weird data here...such as {u'selectedFileName': u'No file selected'}
    :returns dictionary {'file_name': <file_name>, 'file_id': <file__id>}
    if both exist, otherwise {}
    """
    if file:
        name = file.get('selectedFileName', '')
        # viewUrl is the only place the file id is accurate.  On a
        # registration, the other file ids in extra refer to the original
        # file on the node, not the file that was archived on the reg
        view_url = file.get('viewUrl', '')
        file__id = view_url.split('/')[5] if view_url else ''
        if name and file__id:
            return {
                'file_name': name,
                'file_id': file__id
            }
    return {}

# For flatten_registration_metadata
def format_extra(extra):
    """
    Pulls file names, and file ids out of "extra"
    Note: "extra" is typically an array, but for some data, it's a dict

    :returns array of dictionaries, of format
    [{'file_name': <filename>, 'file_id': <file__id>}]
    """
    files = []
    if isinstance(extra, list):
        for file in extra:
            file_info = extract_file_info(file)
            files.append(file_info)
    else:
        file_info = extract_file_info(extra)
        if file_info:
            files.append(file_info)
    return files

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
        extra = format_extra(keyed_value.get('extra', []))
        return extra
    else:
        value = keyed_value.get('value', '')
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
        key = keys.pop(0)
        # Returns the value associated with the given key
        value = get_value_or_extra(nested_response, block_type, key, keys)
        return get_nested_answer(value, block_type, keys)
    else:
        # Once we've drilled down through the entire dictionary, our nested_response
        # should be an array or a string
        return nested_response

# For expanding registration_responses
def set_nested_values(nested_dictionary, keys, value):
    """
    Drills down through the nested dictionary, accessing each key in the array,
    and sets the last key equal to the  passed in value, if this key doesn't already exist.

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
def build_answer_block(block_type, value):
    extra = []
    if block_type == 'file-input':
        extra = value
        value = ''
        for file in extra:
            if file.get('file_name'):
                file['data'] = {
                    'name': file.get('file_name')  # What legacy FE needs for rendering
                }
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
        # All keys from left to right including the current key
        current_chain = keys[0:current_index + 1]
        # If we're on the final key, use the passed in value
        val = value if current_index == len(keys) - 1 else {}
        set_nested_values(metadata, current_chain, val)
        return build_registration_metadata_dict(keys, current_index + 1, metadata, value)
