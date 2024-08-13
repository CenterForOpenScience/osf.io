import json

from osf.metadata.serializers import _base
from .datacite_tree_walker import DataciteTreeWalker


def _visit_tree_branch_json(parent, child_name: str, *, is_list=False, text=None, attrib=None):
    assert isinstance(parent, (dict, list)), (
        f'expected parent to be list or dict, got type {type(parent)} (parent={parent})'
    )
    parent_is_list = isinstance(parent, list)
    if is_list:
        assert not parent_is_list
        if (text is None) and (attrib is None):
            child = []  # normal is_list case
        else:
            # HACK (part 1) to support datacite `affiliation` (repeated item without list wrapper)
            child = _child_json_object(child_name, text, attrib)
    elif text and not attrib and not parent_is_list:
        child = text
    else:
        child = _child_json_object(child_name, text, attrib)
    if parent_is_list:
        parent.append(child)
    else:
        if is_list and isinstance(child, dict):  # HACK (part 2)
            parent.setdefault(child_name, []).append(child)
        else:
            parent[child_name] = child
    return child


def _child_json_object(child_name, text, attrib) -> dict:
    json_obj = {}
    if text is not None:
        try:
            json_obj[child_name] = text.toPython()  # quacks like rdflib.Literal
        except AttributeError:
            json_obj[child_name] = str(text)
        language = getattr(text, 'language', None)
        if language:
            json_obj['lang'] = language
    if attrib is not None:
        assert child_name not in attrib
        json_obj.update(attrib)
    return json_obj


class DataciteJsonMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'application/json'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-datacite.json'

    def serialize(self) -> str:
        return json.dumps(
            self.metadata_as_dict(),
            indent=2,
            sort_keys=True,
        )

    def metadata_as_dict(self) -> dict:
        root_dict = {}
        walker = DataciteTreeWalker(self.basket, root_dict, _visit_tree_branch_json)
        walker.walk(doi_override=self.serializer_config.get('doi_value'))
        return root_dict
