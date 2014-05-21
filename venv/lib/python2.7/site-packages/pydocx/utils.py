import re
import collections

from collections import defaultdict
from xml.etree import cElementTree

from pydocx.exceptions import MalformedDocxException


UPPER_ROMAN_TO_HEADING_VALUE = 'h2'
TAGS_CONTAINING_CONTENT = (
    't',
    'pict',
    'drawing',
    'delText',
    'ins',
)
TAGS_HOLDING_CONTENT_TAGS = (
    'p',
    'tbl',
    'sdt',
)


class MulitMemoize(object):
    '''
    Adapted from: https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    func_names = {
        'find_all': find_all,
        ...
    }
    '''
    def __init__(self, func_names):
        self.cache = dict((func_name, {}) for func_name in func_names)
        self.func_names = func_names

    def __call__(self, func_name, *args):
        if not isinstance(args, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func_names[func_name](*args)
        if args in self.cache[func_name]:
            return self.cache[func_name][args]
        else:
            value = self.func_names[func_name](*args)
            self.cache[func_name][args] = value
            return value


class MulitMemoizeMixin(object):
    def __init__(self, *args, **kwargs):
        super(MulitMemoizeMixin, self).__init__(*args, **kwargs)
        self._memoization = None

    def memod_tree_op(self, func_name, *args):
        return self._memoization(func_name, *args)

    def populate_memoization(self, func_names):
        self._memoization = MulitMemoize(func_names)


def el_iter(el):
    """
    Go through all elements
    """
    try:
        return el.iter()
    except AttributeError:
        return el.findall('.//*')


def find_first(el, tag):
    """
    Find the first occurrence of a tag beneath the current element.
    """
    return el.find('.//' + tag)


def find_all(el, tag):
    """
    Find all occurrences of a tag
    """
    return el.findall('.//' + tag)


def find_ancestor_with_tag(pre_processor, el, tag):
    """
    Find the first ancestor with that is a `tag`.
    """
    while pre_processor.parent(el) is not None:
        el = pre_processor.parent(el)
        if el.tag == tag:
            return el
    return None


def has_descendant_with_tag(el, tag):
    """
    Determine if there is a child ahead in the element tree.
    """
    # Get child. stop at first child.
    return True if find_first(el, tag) is not None else False


def _filter_children(element, tags):
    return [
        el for el in element.getchildren()
        if el.tag in tags
    ]


def remove_namespaces(document):
    """
    >>> exception_raised = False
    >>> try:
    ...     remove_namespaces('junk')
    ... except MalformedDocxException:
    ...     exception_raised = True
    >>> assert exception_raised
    """
    encoding_regex = re.compile(
        r'<\?xml.*encoding="(.+?)"',
        re.DOTALL | re.MULTILINE,
    )
    encoding = 'us-ascii'
    m = encoding_regex.match(document)
    if m:
        encoding = m.groups(0)[0]
    try:
        root = cElementTree.fromstring(document)
    except SyntaxError:
        raise MalformedDocxException('This document cannot be converted.')
    for child in el_iter(root):
        child.tag = child.tag.split("}")[1]
        child.attrib = dict(
            (k.split("}")[-1], v)
            for k, v in child.attrib.items()
        )
    return cElementTree.tostring(root, encoding=encoding)


def get_list_style(numbering_root, num_id, ilvl):
    # This is needed on both the custom lxml parser and the pydocx parser. So
    # make it a function.
    ids = find_all(numbering_root, 'num')
    for _id in ids:
        if _id.attrib['numId'] != num_id:
            continue
        abstractid = _id.find('abstractNumId')
        abstractid = abstractid.attrib['val']
        style_information = find_all(
            numbering_root,
            'abstractNum',
        )
        for info in style_information:
            if info.attrib['abstractNumId'] == abstractid:
                for i in el_iter(info):
                    if (
                            'ilvl' in i.attrib and
                            i.attrib['ilvl'] != ilvl):
                        continue
                    if i.find('numFmt') is not None:
                        return i.find('numFmt').attrib['val']


class NamespacedNumId(object):
    def __init__(self, num_id, num_tables, *args, **kwargs):
        self._num_id = num_id
        self._num_tables = num_tables

    def __unicode__(self, *args, **kwargs):
        return '%s:%d' % (
            self._num_id,
            self._num_tables,
        )

    def __repr__(self, *args, **kwargs):
        return self.__unicode__(*args, **kwargs)

    def __eq__(self, other):
        if other is None:
            return False
        return repr(self) == repr(other)

    def __ne__(self, other):
        if other is None:
            return False
        return repr(self) != repr(other)

    @property
    def num_id(self):
        return self._num_id


class PydocxPreProcessor(MulitMemoizeMixin):
    def __init__(
            self,
            convert_root_level_upper_roman=False,
            styles_dict=None,
            numbering_root=None,
            *args, **kwargs):
        self.meta_data = defaultdict(dict)
        self.convert_root_level_upper_roman = convert_root_level_upper_roman
        self.styles_dict = styles_dict
        self.numbering_root = numbering_root

    def perform_pre_processing(self, root, *args, **kwargs):
        self.populate_memoization({
            'find_first': find_first,
        })
        self._add_parent(root)
        # If we don't have a numbering root there cannot be any lists.
        if self.numbering_root is not None:
            self._set_list_attributes(root)
        self._set_table_attributes(root)
        self._set_is_in_table(root)

        body = find_first(root, 'body')
        p_elements = [
            child for child in find_all(body, 'p')
        ]
        list_elements = [
            child for child in p_elements
            if self.is_list_item(child)
        ]
        # Find the first and last li elements
        num_ids = set([self.num_id(i) for i in list_elements])
        ilvls = set([self.ilvl(i) for i in list_elements])
        self._set_first_list_item(num_ids, ilvls, list_elements)
        self._set_last_list_item(num_ids, list_elements)

        self._set_headers(p_elements)
        self._convert_upper_roman(body)
        self._set_next(body)

    def is_first_list_item(self, el):
        return self.meta_data[el].get('is_first_list_item', False)

    def is_last_list_item_in_root(self, el):
        return self.meta_data[el].get('is_last_list_item_in_root', False)

    def is_list_item(self, el):
        return self.meta_data[el].get('is_list_item', False)

    def num_id(self, el):
        if not self.is_list_item(el):
            return None
        return self.meta_data[el].get('num_id')

    def ilvl(self, el):
        if not self.is_list_item(el):
            return None
        return self.meta_data[el].get('ilvl')

    def heading_level(self, el):
        return self.meta_data[el].get('heading_level')

    def is_in_table(self, el):
        return self.meta_data[el].get('is_in_table')

    def row_index(self, el):
        return self.meta_data[el].get('row_index')

    def column_index(self, el):
        return self.meta_data[el].get('column_index')

    def vmerge_continue(self, el):
        return self.meta_data[el].get('vmerge_continue')

    def next(self, el):
        if el not in self.meta_data:
            return
        return self.meta_data[el].get('next')

    def previous(self, el):
        if el not in self.meta_data:
            return
        return self.meta_data[el].get('previous')

    def parent(self, el):
        return self.meta_data[el].get('parent')

    def _add_parent(self, el):  # if a parent, make that an attribute
        for child in el.getchildren():
            self.meta_data[child]['parent'] = el
            self._add_parent(child)

    def _set_list_attributes(self, el):
        list_elements = find_all(el, 'numId')
        for li in list_elements:
            parent = find_ancestor_with_tag(self, li, 'p')
            # Deleted text in a list will have a numId but no ilvl.
            if parent is None:
                continue
            parent_ilvl = self.memod_tree_op('find_first', parent, 'ilvl')
            if parent_ilvl is None:
                continue
            self.meta_data[parent]['is_list_item'] = True
            self.meta_data[parent]['num_id'] = self._generate_num_id(parent)
            self.meta_data[parent]['ilvl'] = parent_ilvl.attrib['val']

    def _generate_num_id(self, el):
        '''
        Fun fact: It is possible to have a list in the root, that holds a table
        that holds a list and for both lists to have the same numId. When this
        happens we should namespace the nested list with the number of tables
        it is in to ensure it is considered a new list. Otherwise all sorts of
        terrible html gets generated.
        '''
        num_id = find_first(el, 'numId').attrib['val']

        # First, go up the parent until we get None and count the number of
        # tables there are.
        num_tables = 0
        while self.parent(el) is not None:
            if el.tag == 'tbl':
                num_tables += 1
            el = self.parent(el)
        return NamespacedNumId(
            num_id=num_id,
            num_tables=num_tables,
        )

    def _set_first_list_item(self, num_ids, ilvls, list_elements):
        # Lists are grouped by having the same `num_id` and `ilvl`. The first
        # list item is the first list item found for each `num_id` and `ilvl`
        # combination.
        for num_id in num_ids:
            for ilvl in ilvls:
                filtered_list_elements = [
                    i for i in list_elements
                    if (
                        self.num_id(i) == num_id and
                        self.ilvl(i) == ilvl
                    )
                ]
                if not filtered_list_elements:
                    continue
                first_el = filtered_list_elements[0]
                self.meta_data[first_el]['is_first_list_item'] = True

    def _set_last_list_item(self, num_ids, list_elements):
        # Find last list elements. Only mark list tags as the last list tag if
        # it is in the root of the document. This is only used to ensure that
        # once a root level list is finished we do not roll in the rest of the
        # non list elements into the first root level list.
        for num_id in num_ids:
            filtered_list_elements = [
                i for i in list_elements
                if self.num_id(i) == num_id
            ]
            if not filtered_list_elements:
                continue
            last_el = filtered_list_elements[-1]
            self.meta_data[last_el]['is_last_list_item_in_root'] = True

    def _set_table_attributes(self, el):
        tables = find_all(el, 'tbl')
        for table in tables:
            rows = _filter_children(table, ['tr'])
            if rows is None:
                continue
            for i, row in enumerate(rows):
                tcs = _filter_children(row, ['tc'])
                for j, child in enumerate(tcs):
                    self.meta_data[child]['row_index'] = i
                    self.meta_data[child]['column_index'] = j
                    v_merge = find_first(child, 'vMerge')
                    if (
                            v_merge is not None and
                            ('continue' == v_merge.get('val', '') or
                             v_merge.attrib == {})
                    ):
                        self.meta_data[child]['vmerge_continue'] = True

    def _set_is_in_table(self, el):
        paragraph_elements = find_all(el, 'p')
        for p in paragraph_elements:
            if find_ancestor_with_tag(self, p, 'tc') is not None:
                self.meta_data[p]['is_in_table'] = True

    def _set_headers(self, elements):
        # These are the styles for headers and what the html tag should be if
        # we have one.
        headers = {
            'heading 1': 'h1',
            'heading 2': 'h2',
            'heading 3': 'h3',
            'heading 4': 'h4',
            'heading 5': 'h5',
            'heading 6': 'h6',
            'heading 7': 'h6',
            'heading 8': 'h6',
            'heading 9': 'h6',
            'heading 10': 'h6',
        }
        # Remove the rPr from the styles dict since all the styling will be
        # down with the heading.
        for style_id, styles in self.styles_dict.items():
            if styles.get('style_name', '').lower() in headers:
                if 'default_run_properties' in styles:
                    del styles['default_run_properties']

        for element in elements:
            # This element is using the default style which is not a heading.
            p_style = find_first(element, 'pStyle')
            if p_style is None:
                continue
            style = p_style.attrib.get('val', '')
            metadata = self.styles_dict.get(style, {})
            style_name = metadata.get('style_name')

            # Check to see if this element is actually a header.
            if style_name and style_name.lower() in headers:
                # Set all the list item variables to false.
                self.meta_data[element]['is_list_item'] = False
                self.meta_data[element]['is_first_list_item'] = False
                self.meta_data[element]['is_last_list_item_in_root'] = False
                # Prime the heading_level
                self.meta_data[element]['heading_level'] = headers[style_name.lower()]  # noqa

    def _convert_upper_roman(self, body):
        if not self.convert_root_level_upper_roman:
            return
        first_root_list_items = [
            # Only root level elements.
            el for el in body.getchildren()
            # And only first_list_items
            if self.is_first_list_item(el)
        ]
        visited_num_ids = []
        all_p_tags_in_body = find_all(body, 'p')
        for root_list_item in first_root_list_items:
            if self.num_id(root_list_item) in visited_num_ids:
                continue
            visited_num_ids.append(self.num_id(root_list_item))
            lst_style = get_list_style(
                self.numbering_root,
                self.num_id(root_list_item).num_id,
                self.ilvl(root_list_item),
            )
            if lst_style != 'upperRoman':
                continue
            ilvl = min(
                self.ilvl(el) for el in all_p_tags_in_body
                if self.num_id(el) == self.num_id(root_list_item)
            )
            root_upper_roman_list_items = [
                el for el in all_p_tags_in_body
                if self.num_id(el) == self.num_id(root_list_item) and
                self.ilvl(el) == ilvl
            ]
            for list_item in root_upper_roman_list_items:
                self.meta_data[list_item]['is_list_item'] = False
                self.meta_data[list_item]['is_first_list_item'] = False
                self.meta_data[list_item]['is_last_list_item_in_root'] = False  # noqa

                self.meta_data[list_item]['heading_level'] = UPPER_ROMAN_TO_HEADING_VALUE  # noqa

    def _set_next(self, body):
        def _get_children_with_content(el):
            # We only care about children if they have text in them.
            children = []
            for child in _filter_children(el, TAGS_HOLDING_CONTENT_TAGS):
                _has_descendant_with_tag = any(
                    has_descendant_with_tag(child, tag) for
                    tag in TAGS_CONTAINING_CONTENT
                )
                if _has_descendant_with_tag:
                    children.append(child)
            return children

        def _assign_next(children):
            # Populate the `next` attribute for all the child elements.
            for i in range(len(children)):
                try:
                    if children[i + 1] is not None:
                        self.meta_data[children[i]]['next'] = children[i + 1]  # noqa
                except IndexError:
                    pass
                try:
                    if children[i - 1] is not None:
                        self.meta_data[children[i]]['previous'] = children[i - 1]  # noqa
                except IndexError:
                    pass
        # Assign next for everything in the root.
        _assign_next(_get_children_with_content(body))

        # In addition set next for everything in table cells.
        for tc in find_all(body, 'tc'):
            _assign_next(_get_children_with_content(tc))


def parse_xml_from_string(xml):
    return cElementTree.fromstring(remove_namespaces(xml))
