try:
    import hashlib

    _md5func = hashlib.md5
except ImportError:  # for Python < 2.5
    import md5

    _md5func = md5.new

from bson.errors import InvalidId
from bson.py3compat import (PY3, b, binary_type, text_type,
                            bytes_from_hex, string_types)

def _machine_bytes():
    """Get the machine portion of an ObjectId.
    """
    machine_hash = _md5func()
    if PY3:
        # gethostname() returns a unicode string in python 3.x
        # while update() requires a byte string.
        machine_hash.update(socket.gethostname().encode())
    else:
        # Calling encode() here will fail with non-ascii hostnames
        machine_hash.update(socket.gethostname())
    return machine_hash.digest()[0:3]


class ObjectId(object):
    """A MongoDB ObjectId.
    """

    _inc = random.randint(0, 0xFFFFFF)
    _inc_lock = threading.Lock()

    _machine_bytes = _machine_bytes()

    __slots__ = ('__id')

    def __init__(self, oid=None):
        """Initialize a new ObjectId.

        If `oid` is ``None``, create a new (unique) ObjectId. If `oid`
        is an instance of (:class:`basestring` (:class:`str` or :class:`bytes`
        in python 3), :class:`ObjectId`) validate it and use that.  Otherwise,
        a :class:`TypeError` is raised. If `oid` is invalid,
        :class:`~bson.errors.InvalidId` is raised.

        :Parameters:
          - `oid` (optional): a valid ObjectId (12 byte binary or 24 character
            hex string)

        .. versionadded:: 1.2.1
           The `oid` parameter can be a ``unicode`` instance (that contains
           only hexadecimal digits).

        .. mongodoc:: objectids
        """
        if oid is None:
            self.__generate()
        else:
            self.__validate(oid)
