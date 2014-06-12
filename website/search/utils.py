# XML cleanup needed for Solr. Code from
# https://github.com/toastdriven/pysolr/blob/e46ac6d385b9639190d28a3647c2f97c992d008f/pysolr.py

def is_valid_xml_char_ordinal(i):
    """
    Defines whether char is valid to use in xml document

    XML standard defines a valid char as::

    Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    """
    return ( # conditions ordered by presumed frequency
        0x20 <= i <= 0xD7FF
        or i in (0x9, 0xA, 0xD)
        or 0xE000 <= i <= 0xFFFD
        or 0x10000 <= i <= 0x10FFFF
        )


def clean_xml_string(s):
    """
    Cleans string from invalid xml chars

    Solution was found there::

    http://stackoverflow.com/questions/8733233/filtering-out-certain-bytes-in-python
    """
    return ''.join(c for c in s if is_valid_xml_char_ordinal(ord(c)))


def clean_solr_doc(doc):
    """Recursively remove XML-invalid characters from Solr document.

    """
    if isinstance(doc, basestring):
        return clean_xml_string(doc)
    elif isinstance(doc, list):
        return [
            clean_solr_doc(subdoc)
            for subdoc in doc
        ]
    elif isinstance(doc, dict):
        return {
            key: clean_solr_doc(subdoc)
            for key, subdoc in doc.items()
        }
