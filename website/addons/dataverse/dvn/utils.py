__author__="peterbull"
__date__ ="$Aug 16, 2013 12:07:48 PM$"

from lxml import etree
import bleach

REPLACEMENT_DICT = {'id': 'identifier', 'author': 'creator', 'producer': 'publisher', 'restriction': 'rights',
                    'keyword': 'subject', 'publication': 'isReferencedBy'}


class DvnException(Exception):
    pass


# factor out xpath operations so we don't have to look at its ugliness
def get_elements(rootElement, tag=None, namespace=None, attribute=None, attributeValue=None, numberOfElements=None):
    # accept either an lxml.Element or a string of xml
    # if a string, convert to etree element
    if isinstance(rootElement, str):
        rootElement = etree.XML(rootElement)
    
    if namespace == None:
        namespace = rootElement.nsmap[None]
    #namespace = 'http://www.w3.org/1999/xhtml'

    if not tag:
        xpath = "*"
    elif namespace == "":
        xpath = tag
    else:
        xpath = "{{{ns}}}{tg}".format(ns=namespace, tg=tag)

    #print xpath

    if attribute and not attributeValue:
        xpath += "[@{att}]".format(att=attribute)
    elif not attribute and attributeValue:
        raise Exception("You must pass an attribute with attributeValue")
    elif attribute and attributeValue:
        xpath += "[@{att}='{attVal}']".format(att=attribute, attVal=attributeValue)
    
    elements = None
    try:
        elements = rootElement.findall(xpath)
        
        if numberOfElements and len(elements) != numberOfElements:
            raise Exception("Wrong number of elements found. Expected {0} and found {1}.".format(
                numberOfElements,
                len(elements),
            ))
        
    except Exception as e:
        print """
Exception thrown trying to get_elements with the following parameters:
exp='{e}'
xpath='{xp}'
xml=
{xml}""".format(e=e, xp=xpath, xml=etree.tostring(rootElement, pretty_print=True))
    
    retVal = elements
    if len(elements) == 1 and numberOfElements == 1:
        retVal = elements[0]
    elif len(elements) == 0 and numberOfElements:
        retVal = None
    
    return retVal


def format_term(term):
    if term in REPLACEMENT_DICT.keys():
        return 'dcterms_{}'.format(REPLACEMENT_DICT[term])
    else:
        return 'dcterms_{}'.format(term)


def sanitize(value):
    return bleach.clean(value, strip=True, tags=[], attributes=[], styles=[])