import base64
from os import path
from tempfile import NamedTemporaryFile

from nose.plugins.skip import SkipTest
from nose.tools import raises

from pydocx.tests import assert_html_equal, BASE_HTML
from pydocx.parsers.Docx2Html import Docx2Html
from pydocx.DocxParser import ZipFile
from pydocx.exceptions import MalformedDocxException


def convert(path, *args, **kwargs):
    return Docx2Html(path, *args, **kwargs).parsed


def test_extract_html():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'simple.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <p>
          Simple text
        </p>
        <ol list-style-type="decimal">
          <li>one</li>
          <li>two</li>
          <li>three</li>
        </ol>
        <table border="1">
          <tr>
            <td>Cell1</td>
            <td>Cell2</td>
          </tr>
          <tr>
            <td>Cell3</td>
            <td>Cell4</td>
          </tr>
        </table>
    ''')


def test_nested_list():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'nested_lists.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <ol list-style-type="decimal">
            <li>one</li>
            <li>two</li>
            <li>three
                <ol list-style-type="decimal">
                    <li>AAA</li>
                    <li>BBB</li>
                    <li>CCC
                        <ol list-style-type="decimal">
                            <li>alpha</li>
                        </ol>
                    </li>
                </ol>
            </li>
            <li>four</li>
        </ol>
        <ol list-style-type="decimal">
            <li>xxx
                <ol list-style-type="decimal">
                    <li>yyy</li>
                </ol>
            </li>
        </ol>
        <ul>
            <li>www
                <ul>
                    <li>zzz</li>
                </ul>
            </li>
        </ul>
    ''')


def test_simple_list():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'simple_lists.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <ol list-style-type="decimal">
            <li>One</li>
        </ol>
        <ul>
            <li>two</li>
        </ul>
    ''')


def test_inline_tags():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'inline_tags.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % (
        '<p>This sentence has some <strong>bold</strong>, '
        'some <em>italics</em> and some '
        '<span class="pydocx-underline">underline</span>, '
        'as well as a <a href="http://www.google.com/">hyperlink</a>.</p>'
    ))


def test_all_configured_styles():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'all_configured_styles.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <p><strong>aaa</strong></p>
        <p><span class="pydocx-underline">bbb</span></p>
        <p><em>ccc</em></p>
        <p><span class="pydocx-caps">ddd</span></p>
        <p><span class="pydocx-small-caps">eee</span></p>
        <p><span class="pydocx-strike">fff</span></p>
        <p><span class="pydocx-strike">ggg</span></p>
        <p><span class="pydocx-hidden">hhh</span></p>
        <p><span class="pydocx-hidden">iii</span></p>
    ''')


def test_super_and_subscript():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'super_and_subscript.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <p>AAA<sup>BBB</sup></p>
        <p><sub>CCC</sub>DDD</p>
    ''')


def test_unicode():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'greek_alphabet.docx',
    )
    actual_html = convert(file_path)
    assert actual_html is not None
    assert u'\u0391\u03b1' in actual_html


def test_special_chars():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'special_chars.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <p>&amp; &lt; &gt; <a href="https://www.google.com/?test=1&amp;more=2">link</a></p>''')  # noqa


def test_include_tabs():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'include_tabs.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '<p>AAA BBB</p>')


def test_table_col_row_span():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'table_col_row_span.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
      <table border="1">
        <tr>
          <td colspan="2">AAA</td>
        </tr>
        <tr>
          <td rowspan="2">BBB</td>
          <td>CCC</td>
        </tr>
        <tr>
          <td>DDD</td>
        </tr>
        <tr>
          <td>
          <div class='pydocx-right'>EEE
          </div></td>
          <td rowspan="2">FFF</td>
        </tr>
        <tr>
          <td>
           <div class='pydocx-right'>GGG
           </div></td>
        </tr>
      </table>
      <table border="1">
        <tr>
          <td>1</td>
          <td>2</td>
          <td>3</td>
          <td>4</td>
        </tr>
        <tr>
          <td>5</td>
          <td colspan="2" rowspan="2">6</td>
          <td>7</td>
        </tr>
        <tr>
          <td>8</td>
          <td>9</td>
        </tr>
        <tr>
          <td>10</td>
          <td>11</td>
          <td>12</td>
          <td>13</td>
        </tr>
      </table>
    ''')


def test_nested_table_rowspan():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'nested_table_rowspan.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <table border="1">
            <tr>
                <td colspan="2">AAA</td>
            </tr>
            <tr>
                <td>BBB</td>
                <td>
                    <table border="1">
                        <tr>
                            <td rowspan="2">CCC</td>
                            <td>DDD</td>
                        </tr>
                        <tr>
                            <td>EEE</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    ''')


def test_nested_tables():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'nested_tables.docx',
    )
    actual_html = convert(file_path)
    # Find out why br tag is there.
    assert_html_equal(actual_html, BASE_HTML % '''
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
    ''')


def test_list_in_table():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'list_in_table.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <table border="1">
          <tr>
            <td>
              <ol list-style-type="decimal">
                <li>AAA</li>
                <li>BBB</li>
                <li>CCC</li>
              </ol>
            </td>
          </tr>
        </table>
    ''')


def test_tables_in_lists():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'tables_in_lists.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <ol list-style-type="decimal">
            <li>AAA</li>
            <li>BBB
                <table border="1">
                    <tr>
                        <td>CCC</td>
                        <td>DDD</td>
                    </tr>
                    <tr>
                        <td>EEE</td>
                        <td>FFF</td>
                    </tr>
                </table>
            </li>
            <li>GGG</li>
        </ol>
    ''')


def test_track_changes_on():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'track_changes_on.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <p>This was some content.</p>
    ''')


def test_headers():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'headers.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <h1>This is an H1</h1>
        <h2>This is an H2</h2>
        <h3>This is an H3</h3>
        <h4>This is an H4</h4>
        <h5>This is an H5</h5>
        <h6>This is an H6</h6>
        <h6>This is an H7</h6>
        <h6>This is an H8</h6>
        <h6>This is an H9</h6>
        <h6>This is an H10</h6>
    ''')


def test_split_headers():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'split_header.docx',
    )

    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <h1>AAA</h1><p>BBB</p><h1>CCC</h1>
    ''')


def get_image_data(docx_file_path, image_name):
    """
    Return base 64 encoded data for the image_name that is stored in the
    docx_file_path.
    """
    with ZipFile(docx_file_path) as f:
        images = [
            e for e in f.infolist()
            if e.filename == 'word/media/%s' % image_name
        ]
        if not images:
            raise AssertionError('%s not in %s' % (image_name, docx_file_path))
        data = f.read(images[0].filename)
    return base64.b64encode(data)


def test_has_image():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'has_image.docx',
    )

    actual_html = convert(file_path)
    image_data = get_image_data(file_path, 'image1.gif')
    assert_html_equal(actual_html, BASE_HTML % '''
        <p>
            AAA
            <img src="data:image/gif;base64,%s" height="55px" width="260px" />
        </p>
    ''' % image_data)


def test_local_dpi():
    # The image in this file does not have a set height or width, show that the
    # html will generate without it.
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'localDpi.docx',
    )
    actual_html = convert(file_path)
    image_data = get_image_data(file_path, 'image1.jpeg')
    assert_html_equal(actual_html, BASE_HTML % '''
        <p><img src="data:image/jpeg;base64,%s" /></p>
    ''' % image_data)


def test_has_image_using_image_handler():
    raise SkipTest('This needs to be converted to an xml test')
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'has_image.docx',
    )

    def image_handler(*args, **kwargs):
        return 'test'
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <p>AAA<img src="test" height="55" width="260" /></p>
    ''')


def test_headers_with_full_line_styles():
    raise SkipTest('This test is not yet passing')
    # Show that if a natural header is completely bold/italics that
    # bold/italics will get stripped out.
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'headers_with_full_line_styles.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <h2>AAA</h2>
        <h2>BBB</h2>
        <h2><strong>C</strong><em>C</em>C</h2>
    ''')


def test_convert_p_to_h():
    raise SkipTest('This test is not yet passing')
    # Show when it is correct to convert a p tag to an h tag based on
    # bold/italics
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'convert_p_to_h.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <h2>AAA</h2>
        <h2>BBB</h2>
        <p>CCC</p>
        <ol list-style-type="decimal">
            <li><strong>DDD</strong></li>
            <li><em>EEE</em></li>
            <li>FFF</li>
        </ol>
        <table border="1">
            <tr>
                <td><strong>GGG</strong></td>
                <td><em>HHH</em></td>
            </tr>
            <tr>
                <td>III</td>
                <td>JJJ</td>
            </tr>
        </table>
    ''')


def test_fake_headings_by_length():
    raise SkipTest('This test is not yet passing')
    # Show that converting p tags to h tags has a length limit. If the p tag is
    # supposed to be converted to an h tag but has more than seven words in the
    # paragraph do not convert it.
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'fake_headings_by_length.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <h2>Heading.</h2>
        <h2>Still a heading.</h2>
        <p>
        <strong>This is not a heading because it is too many words.</strong>
        </p>
    ''')


def test_shift_enter():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'shift_enter.docx',
    )

    # Test just the convert without clean_html to make sure the first
    # break tag is present.
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <p>AAA<br />BBB</p>
        <p>CCC</p>
        <ol list-style-type="decimal">
            <li>DDD<br />EEE</li>
            <li>FFF</li>
        </ol>
        <table border="1">
            <tr>
                <td>GGG<br />HHH</td>
                <td>III<br />JJJ</td>
            </tr>
            <tr>
                <td>KKK</td>
                <td>LLL</td>
            </tr>
        </table>
    ''')


def test_lists_with_styles():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'lists_with_styles.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <ol list-style-type="decimal">
            <li>AAA</li>
            <li>BBB
                <ol list-style-type="lowerRoman">
                    <li>CCC</li>
                    <li>DDD
                        <ol list-style-type="upperLetter">
                            <li>EEE
                                <ol list-style-type="lowerLetter">
                                    <li>FFF</li>
                                </ol>
                            </li>
                        </ol>
                    </li>
                </ol>
            </li>
        </ol>
    ''')


def test_list_to_header():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'list_to_header.docx',
    )
    actual_html = convert(file_path, convert_root_level_upper_roman=True)
    # It should be noted that list item `GGG` is upper roman in the word
    # document to show that only top level upper romans get converted.
    assert_html_equal(actual_html, BASE_HTML % '''
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
    ''')


def test_has_title():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'has_title.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <p>Title</p>
        <p><div class='pydocx-left'>Text</div></p>
    ''')


def test_upper_alpha_all_bold():
    raise SkipTest('This test is not yet passing')
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'upper_alpha_all_bold.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
        <h2>AAA</h2>
        <h2>BBB</h2>
        <h2>CCC</h2>
    ''')


def test_simple_table():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'simple_table.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <table border="1">
        <tr>
            <td rowspan="2">
                Cell1<br />
                Cell3
            </td>
            <td>Cell2<br />
                And I am writing in the table
            </td>
        </tr>
        <tr>
            <td>Cell4</td>
        </tr>
    </table>
    ''')


def test_justification():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'justification.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <p>
        <div class='pydocx-center'>Center Justified</div>
    </p>
    <p>
        <div class='pydocx-right'>Right justified</div>
    </p>
    <p>
        <div class='pydocx-right' style='margin-right:96.0px;'>
            Right justified and pushed in from right
        </div>
    </p>
    <p>
        <div class='pydocx-center'
                style='margin-left:252.0px;margin-right:96.0px;'>
            Center justified and pushed in from left and it is
            great and it is the coolest thing of all time and I like it and
            I think it is cool
        </div>
    </p>
    <p>
        <div style='margin-left:252.0px;margin-right:96.0px;'>
            Left justified and pushed in from left
        </div>
    </p>
    ''')


def test_missing_style():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'missing_style.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <p>AAA</p>
    ''')


def test_missing_numbering():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'missing_numbering.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <p>AAA</p>
    <p>BBB</p>
    ''')


def test_styled_bolding():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'styled_bolding.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <p><strong>AAA</strong></p>
    <p><strong>BBB</strong></p>
    ''')


def test_no_break_hyphen():
    file_path = path.join(
        path.abspath(path.dirname(__file__)),
        '..',
        'fixtures',
        'no_break_hyphen.docx',
    )
    actual_html = convert(file_path)
    assert_html_equal(actual_html, BASE_HTML % '''
    <p>AAA-BBB</p>
    ''')


@raises(MalformedDocxException)
def test_malformed_docx_exception():
    with NamedTemporaryFile(suffix='.docx') as f:
        convert(f.name)


def _converter(*args, **kwargs):
    # Having a converter that does nothing is the same as if abiword fails to
    # convert.
    pass


#def test_converter_broken():
#    file_path = 'test.doc'
#    assert_raises(
#        ConversionFailed,
#        lambda: convert(file_path, converter=_converter),
#    )


def test_fall_back():
    raise SkipTest('This test is not yet passing')
    file_path = 'test.doc'

    def fall_back(*args, **kwargs):
        return 'success'
    html = convert(file_path, fall_back=fall_back, converter=_converter)
    assert html == 'success'


#@mock.patch('docx2html.core.read_html_file')
#@mock.patch('docx2html.core.get_zip_file_handler')
#def test_html_files(patch_zip_handler, patch_read):
def test_html_files():
    raise SkipTest('This test is not yet passing')

    def raise_assertion(*args, **kwargs):
        raise AssertionError('Should not have called get_zip_file_handler')
    #patch_zip_handler.side_effect = raise_assertion

    def return_text(*args, **kwargs):
        return 'test'
    #patch_read.side_effect = return_text

    # Try with an html file
    file_path = 'test.html'

    html = convert(file_path)
    assert html == 'test'

    # Try again with an htm file.
    file_path = 'test.htm'

    html = convert(file_path)
    assert html == 'test'
