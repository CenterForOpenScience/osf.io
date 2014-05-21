VERSION = (0, 2, 8)
__version__ = '.'.join(map(str, VERSION))
__author__ = "Derek Gulbranson"
__author_email__ = 'derek73@gmail.com'
__license__ = "LGPL"
__url__ = "http://code.google.com/p/python-nameparser"

import sys
if sys.version < '3':

    text_type = unicode
    binary_type = str

    def u(x, encoding=None):
        if encoding:
            return unicode(x, encoding)
        else:
            return unicode(x)

else:
    text_type = str
    binary_type = bytes

    def u(x, encoding=None):
        return text_type(x)


from nameparser.parser import HumanName
