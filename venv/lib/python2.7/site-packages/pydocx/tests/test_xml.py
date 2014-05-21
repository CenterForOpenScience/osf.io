# -*- coding: utf-8 -*-
import os
import time

from nose.plugins.skip import SkipTest

from pydocx.tests.document_builder import DocxBuilder as DXB
from pydocx.tests import (
    XMLDocx2Html,
    _TranslationTestCase,
)
from pydocx.utils import parse_xml_from_string, find_all


class StyleIsOnTestCase(_TranslationTestCase):
    expected_output = """
        <p><strong>AAA</strong></p>
        <p>BBB</p>
        <p>CCC</p>
        <p>DDD</p>
    """

    def get_xml(self):
        tags = [
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('AAA')],
                        rpr=DXB.rpr_tag({'b': None}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('BBB')],
                        rpr=DXB.rpr_tag({'b': 'false'}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('CCC')],
                        rpr=DXB.rpr_tag({'b': '0'}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('DDD')],
                        rpr=DXB.rpr_tag({'u': 'none'}),
                    ),
                ],
            ),
        ]

        body = ''
        for tag in tags:
            body += tag
        xml = DXB.xml(body)
        return xml


class HyperlinkVanillaTestCase(_TranslationTestCase):

    relationship_dict = {
        'rId0': 'www.google.com',
    }

    expected_output = '''
        <p><a href="www.google.com">link</a>.</p>
    '''

    def get_xml(self):
        run_tags = []
        run_tags.append(DXB.r_tag([DXB.t_tag('link')]))
        run_tags = [DXB.hyperlink_tag(r_id='rId0', run_tags=run_tags)]
        run_tags.append(DXB.r_tag([DXB.t_tag('.')]))
        body = DXB.p_tag(run_tags)
        xml = DXB.xml(body)
        return xml


class HyperlinkWithMultipleRunsTestCase(_TranslationTestCase):
    relationship_dict = {
        'rId0': 'www.google.com',
    }

    expected_output = '''
        <p><a href="www.google.com">link</a>.</p>
    '''

    def get_xml(self):
        run_tags = [DXB.r_tag([DXB.t_tag(i)]) for i in 'link']
        run_tags = [DXB.hyperlink_tag(r_id='rId0', run_tags=run_tags)]
        run_tags.append(DXB.r_tag([DXB.t_tag('.')]))
        body = DXB.p_tag(run_tags)
        xml = DXB.xml(body)
        return xml


class HyperlinkNoTextTestCase(_TranslationTestCase):
    relationship_dict = {
        'rId0': 'www.google.com',
    }

    expected_output = ''

    def get_xml(self):
        run_tags = []
        run_tags = [DXB.hyperlink_tag(r_id='rId0', run_tags=run_tags)]
        body = DXB.p_tag(run_tags)
        xml = DXB.xml(body)
        return xml


class HyperlinkNotInRelsDictTestCase(_TranslationTestCase):
    relationship_dict = {
        # 'rId0': 'www.google.com', missing
    }

    expected_output = '<p>link.</p>'

    def get_xml(self):
        run_tags = []
        run_tags.append(DXB.r_tag([DXB.t_tag('link')]))
        run_tags = [DXB.hyperlink_tag(r_id='rId0', run_tags=run_tags)]
        run_tags.append(DXB.r_tag([DXB.t_tag('.')]))
        body = DXB.p_tag(run_tags)
        xml = DXB.xml(body)
        return xml


class HyperlinkWithBreakTestCase(_TranslationTestCase):
    relationship_dict = {
        'rId0': 'www.google.com',
    }

    expected_output = '<p><a href="www.google.com">link<br /></a></p>'

    def get_xml(self):
        run_tags = []
        run_tags.append(DXB.r_tag([DXB.t_tag('link')]))
        run_tags.append(DXB.r_tag([DXB.linebreak()]))
        run_tags = [DXB.hyperlink_tag(r_id='rId0', run_tags=run_tags)]
        body = DXB.p_tag(run_tags)
        xml = DXB.xml(body)
        return xml


class ImageLocal(_TranslationTestCase):
    relationship_dict = {
        'rId0': 'media/image1.jpeg',
        'rId1': 'media/image2.jpeg',
    }
    expected_output = '''
    <p><img src="word/media/image1.jpeg" /></p>
    <p><img src="word/media/image2.jpeg" /></p>
    '''

    def get_xml(self):
        drawing = DXB.drawing(height=None, width=None, r_id='rId0')
        pict = DXB.pict(height=None, width=None, r_id='rId1')
        tags = [
            drawing,
            pict,
        ]
        body = ''
        for el in tags:
            body += el

        xml = DXB.xml(body)
        return xml


class ImageTestCase(_TranslationTestCase):
    relationship_dict = {
        'rId0': 'media/image1.jpeg',
        'rId1': 'media/image2.jpeg',
    }
    expected_output = '''
        <p>
            <img src="word/media/image1.jpeg" height="20px" width="40px" />
        </p>
        <p>
            <img src="word/media/image2.jpeg" height="21pt" width="41pt" />
        </p>
    '''

    def get_xml(self):
        drawing = DXB.drawing(height=20, width=40, r_id='rId0')
        pict = DXB.pict(height=21, width=41, r_id='rId1')
        tags = [
            drawing,
            pict,
        ]
        body = ''
        for el in tags:
            body += el

        xml = DXB.xml(body)
        return xml

    def test_get_image_id(self):
        parser = XMLDocx2Html(
            document_xml=self.get_xml(),
            rels_dict=self.relationship_dict,
        )
        tree = parse_xml_from_string(self.get_xml())
        els = []
        els.extend(find_all(tree, 'drawing'))
        els.extend(find_all(tree, 'pict'))
        image_ids = []
        for el in els:
            image_ids.append(parser._get_image_id(el))
        expected = [
            'rId0',
            'rId1',
        ]
        self.assertEqual(
            set(image_ids),
            set(expected),
        )

    def test_get_image_sizes(self):
        parser = XMLDocx2Html(
            document_xml=self.get_xml(),
            rels_dict=self.relationship_dict,
        )
        tree = parse_xml_from_string(self.get_xml())
        els = []
        els.extend(find_all(tree, 'drawing'))
        els.extend(find_all(tree, 'pict'))
        image_ids = []
        for el in els:
            image_ids.append(parser._get_image_size(el))
        expected = [
            ('40px', '20px'),
            ('41pt', '21pt'),
        ]
        self.assertEqual(
            set(image_ids),
            set(expected),
        )


class ImageNotInRelsDictTestCase(_TranslationTestCase):
    relationship_dict = {
        # 'rId0': 'media/image1.jpeg',
    }
    expected_output = ''

    def get_xml(self):
        drawing = DXB.drawing(height=20, width=40, r_id='rId0')
        body = drawing

        xml = DXB.xml(body)
        return xml


class ImageNoSizeTestCase(_TranslationTestCase):
    relationship_dict = {
        'rId0': os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            '..',
            'fixtures',
            'bullet_go_gray.png',
        )
    }
    image_sizes = {
        'rId0': (0, 0),
    }
    expected_output = '''
        <html>
            <p>
                <img src="%s" />
            </p>
        </html>
    ''' % relationship_dict['rId0']

    @staticmethod
    def image_handler(image_id, relationship_dict):
        return relationship_dict.get(image_id)

    def get_xml(self):
        raise SkipTest(
            'Since we are not using PIL, we do not need this test yet.',
        )
        drawing = DXB.drawing('rId0')
        tags = [
            drawing,
        ]
        body = ''
        for el in tags:
            body += el

        xml = DXB.xml(body)
        return xml


class TableTag(_TranslationTestCase):
    expected_output = '''
        <table border="1">
            <tr>
                <td>AAA</td>
                <td>BBB</td>
            </tr>
            <tr>
                <td>CCC</td>
                <td>DDD</td>
            </tr>
        </table>
    '''

    def get_xml(self):
        cell1 = DXB.table_cell(paragraph=DXB.p_tag('AAA'))
        cell2 = DXB.table_cell(paragraph=DXB.p_tag('CCC'))
        cell3 = DXB.table_cell(paragraph=DXB.p_tag('BBB'))
        cell4 = DXB.table_cell(paragraph=DXB.p_tag('DDD'))
        rows = [DXB.table_row([cell1, cell3]), DXB.table_row([cell2, cell4])]
        table = DXB.table(rows)
        body = table
        xml = DXB.xml(body)
        return xml


class RowSpanTestCase(_TranslationTestCase):

    expected_output = '''
           <table border="1">
            <tr>
                <td rowspan="2">AAA</td>
                <td>BBB</td>
            </tr>
            <tr>
                <td>CCC</td>
            </tr>
        </table>
    '''

    def get_xml(self):
        cell1 = DXB.table_cell(
            paragraph=DXB.p_tag('AAA'), merge=True, merge_continue=False)
        cell2 = DXB.table_cell(
            paragraph=DXB.p_tag(None), merge=False, merge_continue=True)
        cell3 = DXB.table_cell(paragraph=DXB.p_tag('BBB'))
        cell4 = DXB.table_cell(paragraph=DXB.p_tag('CCC'))
        rows = [DXB.table_row([cell1, cell3]), DXB.table_row([cell2, cell4])]
        table = DXB.table(rows)
        body = table
        xml = DXB.xml(body)
        return xml


class NestedTableTag(_TranslationTestCase):
    expected_output = '''
        <table border="1">
            <tr>
                <td>AAA</td>
                <td>BBB</td>
            </tr>
            <tr>
                <td>CCC</td>
                <td>
                    <table border="1">
                        <tr>
                            <td>DDD</td>
                            <td>EEE</td>
                        </tr>
                        <tr>
                            <td>FFF</td>
                            <td>GGG</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    '''

    def get_xml(self):
        cell1 = DXB.table_cell(paragraph=DXB.p_tag('DDD'))
        cell2 = DXB.table_cell(paragraph=DXB.p_tag('FFF'))
        cell3 = DXB.table_cell(paragraph=DXB.p_tag('EEE'))
        cell4 = DXB.table_cell(paragraph=DXB.p_tag('GGG'))
        rows = [DXB.table_row([cell1, cell3]), DXB.table_row([cell2, cell4])]
        nested_table = DXB.table(rows)
        cell1 = DXB.table_cell(paragraph=DXB.p_tag('AAA'))
        cell2 = DXB.table_cell(paragraph=DXB.p_tag('CCC'))
        cell3 = DXB.table_cell(paragraph=DXB.p_tag('BBB'))
        cell4 = DXB.table_cell(nested_table)
        rows = [DXB.table_row([cell1, cell3]), DXB.table_row([cell2, cell4])]
        table = DXB.table(rows)
        body = table
        xml = DXB.xml(body)
        return xml


class TableWithInvalidTag(_TranslationTestCase):
    expected_output = '''
        <table border="1">
            <tr>
                <td>AAA</td>
                <td>BBB</td>
            </tr>
            <tr>
                <td></td>
                <td>DDD</td>
            </tr>
        </table>
    '''

    def get_xml(self):
        cell1 = DXB.table_cell(paragraph=DXB.p_tag('AAA'))
        cell2 = DXB.table_cell('<w:invalidTag>CCC</w:invalidTag>')
        cell3 = DXB.table_cell(paragraph=DXB.p_tag('BBB'))
        cell4 = DXB.table_cell(paragraph=DXB.p_tag('DDD'))
        rows = [DXB.table_row([cell1, cell3]), DXB.table_row([cell2, cell4])]
        table = DXB.table(rows)
        body = table
        xml = DXB.xml(body)
        return xml


class TableWithListAndParagraph(_TranslationTestCase):
    expected_output = '''
        <table border="1">
            <tr>
                <td>
                    <ol list-style-type="decimal">
                        <li>AAA</li>
                        <li>BBB</li>
                    </ol>
                    CCC<br />
                    DDD
                </td>
            </tr>
        </table>
    '''

    def get_xml(self):
        li_text = [
            ('AAA', 0, 1),
            ('BBB', 0, 1),
        ]
        lis = ''
        for text, ilvl, numId in li_text:
            lis += DXB.li(text=text, ilvl=ilvl, numId=numId)
        els = [
            lis,
            DXB.p_tag('CCC'),
            DXB.p_tag('DDD'),
        ]
        td = ''
        for el in els:
            td += el
        cell1 = DXB.table_cell(td)
        row = DXB.table_row([cell1])
        table = DXB.table([row])
        body = table
        xml = DXB.xml(body)
        return xml


class SimpleListTestCase(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="lowerLetter">
            <li>AAA</li>
            <li>BBB</li>
            <li>CCC</li>
        </ol>
    '''

    # Ensure its not failing somewhere and falling back to decimal
    numbering_dict = {
        '1': {
            '0': 'lowerLetter',
        }
    }

    def get_xml(self):
        li_text = [
            ('AAA', 0, 1),
            ('BBB', 0, 1),
            ('CCC', 0, 1),
        ]
        lis = ''
        for text, ilvl, numId in li_text:
            lis += DXB.li(text=text, ilvl=ilvl, numId=numId)

        xml = DXB.xml(lis)
        return xml


class SingleListItemTestCase(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="lowerLetter">
            <li>AAA</li>
        </ol>
    '''

    # Ensure its not failing somewhere and falling back to decimal
    numbering_dict = {
        '1': {
            '0': 'lowerLetter',
        }
    }

    def get_xml(self):
        li_text = [
            ('AAA', 0, 1),
        ]
        lis = ''
        for text, ilvl, numId in li_text:
            lis += DXB.li(text=text, ilvl=ilvl, numId=numId)

        xml = DXB.xml(lis)
        return xml


class ListWithContinuationTestCase(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="decimal">
            <li>AAA<br />BBB</li>
            <li>CCC
                <table border="1">
                    <tr>
                        <td>DDD</td>
                        <td>EEE</td>
                    </tr>
                    <tr>
                        <td>FFF</td>
                        <td>GGG</td>
                    </tr>
                </table>
            </li>
            <li>HHH</li>
        </ol>
    '''

    def get_xml(self):
        cell1 = DXB.table_cell(paragraph=DXB.p_tag('DDD'))
        cell2 = DXB.table_cell(paragraph=DXB.p_tag('FFF'))
        cell3 = DXB.table_cell(paragraph=DXB.p_tag('EEE'))
        cell4 = DXB.table_cell(paragraph=DXB.p_tag('GGG'))
        rows = [DXB.table_row([cell1, cell3]), DXB.table_row([cell2, cell4])]
        table = DXB.table(rows)
        tags = [
            DXB.li(text='AAA', ilvl=0, numId=1),
            DXB.p_tag('BBB'),
            DXB.li(text='CCC', ilvl=0, numId=1),
            table,
            DXB.li(text='HHH', ilvl=0, numId=1),
        ]
        body = ''
        for el in tags:
            body += el

        xml = DXB.xml(body)
        return xml


class ListWithMultipleContinuationTestCase(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="decimal">
            <li>AAA
                <table border="1">
                    <tr>
                        <td>BBB</td>
                    </tr>
                </table>
                <table border="1">
                    <tr>
                        <td>CCC</td>
                    </tr>
                </table>
            </li>
            <li>DDD</li>
        </ol>
    '''

    def get_xml(self):
        cell = DXB.table_cell(paragraph=DXB.p_tag('BBB'))
        row = DXB.table_row([cell])
        table1 = DXB.table([row])
        cell = DXB.table_cell(paragraph=DXB.p_tag('CCC'))
        row = DXB.table_row([cell])
        table2 = DXB.table([row])
        tags = [
            DXB.li(text='AAA', ilvl=0, numId=1),
            table1,
            table2,
            DXB.li(text='DDD', ilvl=0, numId=1),
        ]
        body = ''
        for el in tags:
            body += el

        xml = DXB.xml(body)
        return xml


class MangledIlvlTestCase(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="lowerLetter">
            <li>AAA</li>
        </ol>
        <ol list-style-type="decimal">
            <li>BBB
                <ol list-style-type="decimal">
                    <li>CCC</li>
                </ol>
            </li>
        </ol>
    '''

    def get_xml(self):
        li_text = [
            ('AAA', 0, 2),
            ('BBB', 1, 1),
            ('CCC', 0, 1),
        ]
        lis = ''
        for text, ilvl, numId in li_text:
            lis += DXB.li(text=text, ilvl=ilvl, numId=numId)

        xml = DXB.xml(lis)
        return xml


class SeperateListsTestCase(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="lowerLetter">
            <li>AAA</li>
        </ol>
        <ol list-style-type="decimal">
            <li>BBB</li>
        </ol>
        <ol list-style-type="lowerLetter">
            <li>CCC</li>
        </ol>
    '''

    def get_xml(self):
        li_text = [
            ('AAA', 0, 2),
            # Because AAA and CCC are part of the same list (same list id)
            # and BBB is different, these need to be split into three
            # lists (or lose everything from BBB and after.
            ('BBB', 0, 1),
            ('CCC', 0, 2),
        ]
        lis = ''
        for text, ilvl, numId in li_text:
            lis += DXB.li(text=text, ilvl=ilvl, numId=numId)

        xml = DXB.xml(lis)
        return xml


class InvalidIlvlOrderTestCase(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="decimal">
            <li>AAA
                <ol list-style-type="decimal">
                    <li>BBB
                        <ol list-style-type="decimal">
                            <li>CCC</li>
                        </ol>
                    </li>
                </ol>
            </li>
        </ol>
    '''

    def get_xml(self):
        tags = [
            DXB.li(text='AAA', ilvl=1, numId=1),
            DXB.li(text='BBB', ilvl=3, numId=1),
            DXB.li(text='CCC', ilvl=2, numId=1),
        ]
        body = ''
        for el in tags:
            body += el

        xml = DXB.xml(body)
        return xml


class DeeplyNestedTableTestCase(_TranslationTestCase):
    expected_output = ''
    run_expected_output = False

    def get_xml(self):
        paragraph = DXB.p_tag('AAA')

        for _ in range(1000):
            cell = DXB.table_cell(paragraph)
            row = DXB.table_cell([cell])
            table = DXB.table([row])
        body = table
        xml = DXB.xml(body)
        return xml

    def test_performance(self):
        with self.toggle_run_expected_output():
            start_time = time.time()
            try:
                self.test_expected_output()
            except AssertionError:
                pass
            end_time = time.time()
            total_time = end_time - start_time
            # This finishes in under a second on python 2.7
            assert total_time < 3, total_time


class LargeCellTestCase(_TranslationTestCase):
    expected_output = ''
    run_expected_output = False

    def get_xml(self):
        # Make sure it is over 1000 (which is the recursion limit)
        paragraphs = [DXB.p_tag('%d' % i) for i in range(1000)]
        cell = DXB.table_cell(paragraphs)
        row = DXB.table_cell([cell])
        table = DXB.table([row])
        body = table
        xml = DXB.xml(body)
        return xml

    def test_performance(self):
        with self.toggle_run_expected_output():
            start_time = time.time()
            try:
                self.test_expected_output()
            except AssertionError:
                pass
            end_time = time.time()
            total_time = end_time - start_time
            # This finishes in under a second on python 2.7
            assert total_time < 3, total_time


class NonStandardTextTagsTestCase(_TranslationTestCase):
    expected_output = '''
        <p><span class='pydocx-insert'>insert </span>
        smarttag</p>
    '''

    def get_xml(self):
        run_tags = [DXB.r_tag([DXB.t_tag(i)]) for i in 'insert ']
        insert_tag = DXB.insert_tag(run_tags)
        run_tags = [DXB.r_tag([DXB.t_tag(i)]) for i in 'smarttag']
        smart_tag = DXB.smart_tag(run_tags)

        run_tags = [insert_tag, smart_tag]
        body = DXB.p_tag(run_tags)
        xml = DXB.xml(body)
        return xml


class RTagWithNoText(_TranslationTestCase):
    expected_output = ''

    def get_xml(self):
        p_tag = DXB.p_tag(None)  # No text
        run_tags = [p_tag]
        # The bug is only present in a hyperlink
        run_tags = [DXB.hyperlink_tag(r_id='rId0', run_tags=run_tags)]
        body = DXB.p_tag(run_tags)

        xml = DXB.xml(body)
        return xml


class DeleteTagInList(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="decimal">
            <li>AAA
                <span class='pydocx-delete'>BBB</span>
            </li>
            <li>CCC</li>
        </ol>
    '''

    def get_xml(self):
        delete_tags = DXB.delete_tag(['BBB'])
        p_tag = DXB.p_tag([delete_tags])

        body = DXB.li(text='AAA', ilvl=0, numId=0)
        body += p_tag
        body += DXB.li(text='CCC', ilvl=0, numId=0)

        xml = DXB.xml(body)
        return xml


class InsertTagInList(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="decimal">
            <li>AAA<span class='pydocx-insert'>BBB</span>
            </li>
            <li>CCC</li>
        </ol>
    '''

    def get_xml(self):
        run_tags = [DXB.r_tag([DXB.t_tag(i)]) for i in 'BBB']
        insert_tags = DXB.insert_tag(run_tags)
        p_tag = DXB.p_tag([insert_tags])

        body = DXB.li(text='AAA', ilvl=0, numId=0)
        body += p_tag
        body += DXB.li(text='CCC', ilvl=0, numId=0)

        xml = DXB.xml(body)
        return xml


class SmartTagInList(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="decimal">
            <li>AAABBB
            </li>
            <li>CCC</li>
        </ol>
    '''

    def get_xml(self):
        run_tags = [DXB.r_tag([DXB.t_tag(i)]) for i in 'BBB']
        smart_tag = DXB.smart_tag(run_tags)
        p_tag = DXB.p_tag([smart_tag])

        body = DXB.li(text='AAA', ilvl=0, numId=0)
        body += p_tag
        body += DXB.li(text='CCC', ilvl=0, numId=0)

        xml = DXB.xml(body)
        return xml


class SingleListItem(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="lowerLetter">
            <li>AAA</li>
        </ol>
        <p>BBB</p>
    '''

    numbering_dict = {
        '1': {
            '0': 'lowerLetter',
        }
    }

    def get_xml(self):
        li = DXB.li(text='AAA', ilvl=0, numId=1)
        p_tags = [
            DXB.p_tag('BBB'),
        ]
        body = li
        for p_tag in p_tags:
            body += p_tag
        xml = DXB.xml(body)
        return xml


class SimpleTableTest(_TranslationTestCase):
    expected_output = '''
        <table border="1">
            <tr>
                <td>Blank</td>
                <td>Column 1</td>
                <td>Column 2</td>
            </tr>
            <tr>
                <td>Row 1</td>
                <td>First</td>
                <td>Second</td>
            </tr>
            <tr>
                <td>Row 2</td>
                <td>Third</td>
                <td>Fourth</td>
            </tr>
        </table>'''

    def get_xml(self):
        cell1 = DXB.table_cell(paragraph=DXB.p_tag('Blank'))
        cell2 = DXB.table_cell(paragraph=DXB.p_tag('Row 1'))
        cell3 = DXB.table_cell(paragraph=DXB.p_tag('Row 2'))
        cell4 = DXB.table_cell(paragraph=DXB.p_tag('Column 1'))
        cell5 = DXB.table_cell(paragraph=DXB.p_tag('First'))
        cell6 = DXB.table_cell(paragraph=DXB.p_tag('Third'))
        cell7 = DXB.table_cell(paragraph=DXB.p_tag('Column 2'))
        cell8 = DXB.table_cell(paragraph=DXB.p_tag('Second'))
        cell9 = DXB.table_cell(paragraph=DXB.p_tag('Fourth'))
        rows = [DXB.table_row([cell1, cell4, cell7]),
                DXB.table_row([cell2, cell5, cell8]),
                DXB.table_row([cell3, cell6, cell9])]
        table = DXB.table(rows)
        body = table
        xml = DXB.xml(body)
        return xml


class MissingIlvl(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="decimal">
            <li>AAA<br />
                BBB
            </li>
            <li>CCC</li>
        </ol>
    '''

    def get_xml(self):
        li_text = [
            ('AAA', 0, 1),
            ('BBB', None, 1),  # Because why not.
            ('CCC', 0, 1),
        ]
        lis = ''
        for text, ilvl, numId in li_text:
            lis += DXB.li(text=text, ilvl=ilvl, numId=numId)
        body = lis
        xml = DXB.xml(body)
        return xml


class SameNumIdInTable(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="lowerLetter">
            <li>AAA
                <table border="1">
                    <tr>
                        <td>
                            <ol list-style-type="lowerLetter">
                                <li>BBB</li>
                            </ol>
                        </td>
                    </tr>
                </table>
            </li>
            <li>CCC</li>
        </ol>
    '''

    # Ensure its not failing somewhere and falling back to decimal
    numbering_dict = {
        '1': {
            '0': 'lowerLetter',
        }
    }

    def get_xml(self):
        li_text = [
            ('BBB', 0, 1),
        ]
        lis = ''
        for text, ilvl, numId in li_text:
            lis += DXB.li(text=text, ilvl=ilvl, numId=numId)
        cell1 = DXB.table_cell(lis)
        rows = DXB.table_row([cell1])
        table = DXB.table([rows])
        lis = ''
        lis += DXB.li(text='AAA', ilvl=0, numId=1)
        lis += table
        lis += DXB.li(text='CCC', ilvl=0, numId=1)
        body = lis
        xml = DXB.xml(body)
        return xml


class SDTTestCase(_TranslationTestCase):
    expected_output = '''
        <ol list-style-type="decimal">
            <li>AAABBB
            </li>
            <li>CCC</li>
        </ol>
    '''

    def get_xml(self):
        body = ''
        body += DXB.li(text='AAA', ilvl=0, numId=0)
        body += DXB.sdt_tag(p_tag=DXB.p_tag(text='BBB'))
        body += DXB.li(text='CCC', ilvl=0, numId=0)

        xml = DXB.xml(body)
        return xml


class HeadingTestCase(_TranslationTestCase):
    expected_output = '''
        <h1>AAA</h1>
        <h2>BBB</h2>
        <h3>CCC</h3>
        <h4>DDD</h4>
        <h5>EEE</h5>
        <h6>GGG</h6>
        <p>HHH</p>
    '''

    styles_dict = {
        'style0': {
            'style_name': 'heading 1',
        },
        'style1': {
            'style_name': 'heading 2',
        },
        'style2': {
            'style_name': 'heading 3',
        },
        'style3': {
            'style_name': 'heading 4',
        },
        'style4': {
            'style_name': 'heading 5',
        },
        'style5': {
            'style_name': 'heading 6',
        },
    }

    def get_xml(self):
        p_tags = [
            DXB.p_tag(text='AAA', style='style0'),
            DXB.p_tag(text='BBB', style='style1'),
            DXB.p_tag(text='CCC', style='style2'),
            DXB.p_tag(text='DDD', style='style3'),
            DXB.p_tag(text='EEE', style='style4'),
            DXB.p_tag(text='GGG', style='style5'),
            DXB.p_tag(text='HHH', style='garbage'),
        ]
        body = ''
        for tag in p_tags:
            body += tag

        xml = DXB.xml(body)
        return xml


class StyledBoldingTestCase(_TranslationTestCase):
    expected_output = '''
        <p><strong>AAA</strong></p>
        <p><strong>BBB</strong></p>
        <p>CCC</p>
    '''

    styles_dict = {
        'style0': {
            'style_name': 'p1',
            'default_run_properties': {
                'b': '',
            }
        },
    }

    def get_xml(self):
        p_tags = [
            DXB.p_tag(text='AAA', style='style0'),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('BBB')],
                        # Don't do duplicates
                        rpr=DXB.rpr_tag({'b': None}),
                    ),
                ],
                style='style0',
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('CCC')],
                        # Overwrite the current style
                        rpr=DXB.rpr_tag({'b': 'false'}),
                    ),
                ],
                style='style0',
            ),
        ]
        body = ''
        for tag in p_tags:
            body += tag

        xml = DXB.xml(body)
        return xml


class RomanNumeralToHeadingTestCase(_TranslationTestCase):
    convert_root_level_upper_roman = True
    numbering_dict = {
        '1': {
            '0': 'upperRoman',
            '1': 'decimal',
            '2': 'upperRoman',
        },
        '2': {
            '0': 'upperRoman',
            '1': 'decimal',
            '2': 'upperRoman',
        },
        '3': {
            '0': 'upperRoman',
            '1': 'decimal',
            '2': 'upperRoman',
        },
    }
    expected_output = '''
        <h2>AAA</h2>
        <ol list-style-type="decimal">
            <li>BBB</li>
        </ol>
        <h2>CCC</h2>
        <ol list-style-type="decimal">
            <li>DDD</li>
        </ol>
        <h2>EEE</h2>
        <ol list-style-type="decimal">
            <li>FFF
                <ol list-style-type="upperRoman">
                    <li>GGG</li>
                </ol>
            </li>
        </ol>
    '''

    def get_xml(self):
        li_text = [
            ('AAA', 0, 1),
            ('BBB', 1, 1),
            ('CCC', 0, 2),
            ('DDD', 1, 2),
            ('EEE', 0, 3),
            ('FFF', 1, 3),
            ('GGG', 2, 3),
        ]
        body = ''
        for text, ilvl, numId in li_text:
            body += DXB.li(text=text, ilvl=ilvl, numId=numId)

        xml = DXB.xml(body)
        return xml


class MultipleTTagsInRTag(_TranslationTestCase):
    expected_output = '''
        <p>ABC</p>
    '''

    def get_xml(self):
        r_tag = DXB.r_tag(
            [DXB.t_tag(letter) for letter in 'ABC'],
        )
        p_tag = DXB.p_tag(
            [r_tag],
            jc='start',
        )
        body = p_tag

        xml = DXB.xml(body)
        return xml


class SuperAndSubScripts(_TranslationTestCase):
    expected_output = '''
        <p>AAA<sup>BBB</sup></p>
        <p><sub>CCC</sub>DDD</p>
    '''

    def get_xml(self):
        p_tags = [
            DXB.p_tag(
                [
                    DXB.r_tag([DXB.t_tag('AAA')]),
                    DXB.r_tag(
                        [DXB.t_tag('BBB')],
                        rpr=DXB.rpr_tag({'vertAlign': 'superscript'}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('CCC')],
                        rpr=DXB.rpr_tag({'vertAlign': 'subscript'}),
                    ),
                    DXB.r_tag([DXB.t_tag('DDD')]),
                ],
            ),
        ]
        body = ''
        for p_tag in p_tags:
            body += p_tag

        xml = DXB.xml(body)
        return xml


class AvaliableInlineTags(_TranslationTestCase):
    expected_output = '''
        <p><strong>aaa</strong></p>
        <p><span class="pydocx-underline">bbb</span></p>
        <p><em>ccc</em></p>
        <p><span class="pydocx-caps">ddd</span></p>
        <p><span class="pydocx-small-caps">eee</span></p>
        <p><span class="pydocx-strike">fff</span></p>
        <p><span class="pydocx-strike">ggg</span></p>
        <p><span class="pydocx-hidden">hhh</span></p>
        <p><span class="pydocx-hidden">iii</span></p>
        <p><sup>jjj</sup></p>
    '''

    def get_xml(self):
        p_tags = [
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('aaa')],
                        rpr=DXB.rpr_tag({'b': None}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('bbb')],
                        rpr=DXB.rpr_tag({'u': None}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('ccc')],
                        rpr=DXB.rpr_tag({'i': None}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('ddd')],
                        rpr=DXB.rpr_tag({'caps': None}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('eee')],
                        rpr=DXB.rpr_tag({'smallCaps': None}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('fff')],
                        rpr=DXB.rpr_tag({'strike': None})
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('ggg')],
                        rpr=DXB.rpr_tag({'dstrike': None}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('hhh')],
                        rpr=DXB.rpr_tag({'vanish': None})
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('iii')],
                        rpr=DXB.rpr_tag({'webHidden': None}),
                    ),
                ],
            ),
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag('jjj')],
                        rpr=DXB.rpr_tag({'vertAlign': 'superscript'}),
                    ),
                ],
            ),
        ]
        body = ''
        for p_tag in p_tags:
            body += p_tag

        xml = DXB.xml(body)
        return xml


class UnicodeTestCase(_TranslationTestCase):
    expected_output = u"""
        <p>\U0010001f</p>
    """

    def get_xml(self):
        tags = [
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag(r'&#x10001F;')],
                    ),
                ],
            ),
        ]

        body = ''
        for tag in tags:
            body += tag
        xml = DXB.xml(body)
        return xml.encode('utf-8')


class NoTextInTTagTestCase(_TranslationTestCase):
    expected_output = u"""
    """

    def get_xml(self):
        tags = [
            DXB.p_tag(
                [
                    DXB.r_tag(
                        [DXB.t_tag(None)],
                    ),
                ],
            ),
        ]

        body = ''
        for tag in tags:
            body += tag
        xml = DXB.xml(body)
        return xml.encode('utf-8')
