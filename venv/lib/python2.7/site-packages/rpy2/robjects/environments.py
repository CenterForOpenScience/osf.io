import rpy2.rinterface as rinterface
from rpy2.robjects.robject import RObjectMixin, RObject
import conversion

_new_env = rinterface.baseenv["new.env"]

class Environment(RObjectMixin, rinterface.SexpEnvironment):
    """ An R environement. """
    
    def __init__(self, o=None):
        if o is None:
            o = _new_env(hash=rinterface.SexpVector([True, ], 
                                                    rinterface.LGLSXP))
        super(Environment, self).__init__(o)

    def __getitem__(self, item):
        res = super(Environment, self).__getitem__(item)
        res = conversion.ri2py(res)
        res.__rname__ = item
        return res

    def __setitem__(self, item, value):
        robj = conversion.py2ro(value)
        super(Environment, self).__setitem__(item, robj)

    def get(self, item, wantfun = False):
        """ Get a object from its R name/symol
        :param item: string (name/symbol)
        :rtype: object (as returned by :func:`conversion.ri2py`)
        """
        res = super(Environment, self).get(item, wantfun = wantfun)
        res = conversion.ri2py(res)
        res.__rname__ = item
        return res

    def keys(self):
        """ Return a tuple listing the keys in the object """
        return tuple([x for x in self])
