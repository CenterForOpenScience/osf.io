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
