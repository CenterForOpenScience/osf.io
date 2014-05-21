from collections import OrderedDict
from rpy2.robjects.robject import RObjectMixin, RObject
import rpy2.rinterface as rinterface
#import rpy2.robjects.conversion as conversion
import conversion

baseenv_ri = rinterface.baseenv

#needed to avoid circular imports
_reval = rinterface.baseenv['eval']
NULL = _reval(rinterface.parse("NULL"))


class Function(RObjectMixin, rinterface.SexpClosure):
    """ Python representation of an R function.
    """

    __formals = baseenv_ri.get('formals')
    __local = baseenv_ri.get('local')
    __call = baseenv_ri.get('call')
    __assymbol = baseenv_ri.get('as.symbol')
    __newenv = baseenv_ri.get('new.env')

    _local_env = None

    def __init__(self, *args, **kwargs):
        super(Function, self).__init__(*args, **kwargs)
        self._local_env = self.__newenv(hash=rinterface.BoolSexpVector((True, )))

    def __call__(self, *args, **kwargs):
        new_args = [conversion.py2ri(a) for a in args]
        new_kwargs = {}
        for k, v in kwargs.iteritems():
            new_kwargs[k] = conversion.py2ri(v)
        res = super(Function, self).__call__(*new_args, **new_kwargs)
        res = conversion.ri2py(res)
        return res

    def formals(self):
        """ Return the signature of the underlying R function 
        (as the R function 'formals()' would).
        """
        res = self.__formals(self)
        res = conversion.ri2py(res)
        return res

    def rcall(self, *args):
        """ Wrapper around the parent method rpy2.rinterface.SexpClosure.rcall(). """
        res = super(Function, self).rcall(*args)
        res = conversion.ri2py(res)
        return res

class SignatureTranslatedFunction(Function):
    """ Python representation of an R function, where
    the character '.' is replaced with '_' in the R arguments names. """
    _prm_translate = None

    def __init__(self, sexp, init_prm_translate = None):
        super(SignatureTranslatedFunction, self).__init__(sexp)
        if init_prm_translate is None:
            prm_translate = OrderedDict()
        else:
            assert isinstance(init_prm_translate, dict)
            prm_translate = init_prm_translate
        if not self.formals().rsame(NULL):
            for r_param in self.formals().names:
                py_param = r_param.replace('.', '_')
                if py_param in prm_translate:
                    raise ValueError("Error: '%s' already in the transalation table" %r_param)
                #FIXME: systematically add the parameter to the translation, as it makes it faster for generating
                # dynamically the pydoc string from the R help.
                #if py_param != r_param:
                #    prm_translate[py_param] = r_param
                prm_translate[py_param] = r_param
        self._prm_translate = prm_translate
        if hasattr(sexp, '__rname__'):
            self.__rname__ = sexp.__rname__

    def __call__(self, *args, **kwargs):
        prm_translate = self._prm_translate
        for k in tuple(kwargs.keys()):
            r_k = prm_translate.get(k, None)
            if r_k is not None:
                v = kwargs.pop(k)
                kwargs[r_k] = v
        return super(SignatureTranslatedFunction, self).__call__(*args, **kwargs)
