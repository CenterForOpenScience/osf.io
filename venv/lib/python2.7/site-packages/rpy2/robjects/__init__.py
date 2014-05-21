"""
R objects as Python objects.

The module is structured around the singleton r of class R,
that represents an embedded R.

License: GPLv3.0 (although a dual license can be worked out)

"""

import os, sys
import array
import itertools
from datetime import datetime
import rpy2.rinterface as rinterface
import rpy2.rlike.container as rlc

from rpy2.robjects.robject import RObjectMixin, RObject
from rpy2.robjects.vectors import *
from rpy2.robjects.functions import Function, SignatureTranslatedFunction
from rpy2.robjects.environments import Environment
from rpy2.robjects.methods import RS4

import conversion

from rpy2.rinterface import Sexp, SexpVector, SexpClosure, SexpEnvironment, SexpS4, SexpExtPtr
_globalenv = rinterface.globalenv

# missing values
from rpy2.rinterface import NA_Real, NA_Integer, NA_Logical, NA_Character, NA_Complex, NULL

_reval = rinterface.baseenv['eval']

def reval(string, envir = _globalenv):
    """ Evaluate a string as R code
    - string: a string
    - envir: an environment in which the environment should take place
             (default: R's global environment)
    """
    p = rinterface.parse(string)
    res = _reval(p, envir = envir)
    return res

#FIXME: close everything when leaving (check RPy for that).

def default_ri2py(o):
    """ Convert an :class:`rpy2.rinterface.Sexp` object to a higher-level object,
    without copying the R object.

    :param o: object
    :rtype: :class:`rpy2.robjects.RObject` (and subclasses)
    """

    res = None
    try:
        rcls = o.do_slot("class")
    except LookupError, le:
        rcls = [None]

    if isinstance(o, RObject):
        res = o
    elif isinstance(o, SexpVector):
        if 'data.frame' in rcls:
            res = vectors.DataFrame(o)
        if res is None:
            try:
                dim = o.do_slot("dim")
                if len(dim) == 2:
                    res = vectors.Matrix(o)
                else:
                    res = vectors.Array(o)
            except LookupError, le:
                if o.typeof == rinterface.INTSXP:
                    if 'factor' in rcls:
                        res = vectors.FactorVector(o)
                    else:
                        res = vectors.IntVector(o)
                elif o.typeof == rinterface.REALSXP:
                    if o.rclass[0] == 'POSIXct':
                        res = vectors.POSIXct(o)
                    else:
                        res = vectors.FloatVector(o)
                elif o.typeof == rinterface.STRSXP:
                    res = vectors.StrVector(o)
                elif o.typeof == rinterface.VECSXP:
                    res = vectors.ListVector(o)
                elif o.typeof == rinterface.LANGSXP and 'formula' in rcls:
                    res = Formula(o)
                else:
                    res = vectors.Vector(o)

    elif isinstance(o, SexpClosure):
        res = SignatureTranslatedFunction(o)
    elif isinstance(o, SexpEnvironment):
        res = Environment(o)
    elif isinstance(o, SexpS4):
        res = RS4(o)
    elif isinstance(o, SexpExtPtr):
        res = o
    elif o is NULL:
        res = o
    else:
        res = RObject(o)
    return res

conversion.ri2py = default_ri2py


def default_py2ri(o):
    """ Convert an arbitrary Python object to an :class:`rpy2.rinterface.Sexp` object.
    Creates an R object with the content of the Python object,
    wich means data copying.

    :param o: object
    :rtype: :class:`rpy2.rinterface.Sexp` (and subclasses)
    """

    if isinstance(o, RObject):
        res = rinterface.Sexp(o)
    if isinstance(o, Sexp):
        res = o
    elif isinstance(o, array.array):
        if o.typecode in ('h', 'H', 'i', 'I'):
            res = rinterface.SexpVector(o, rinterface.INTSXP)
        elif o.typecode in ('f', 'd'):
            res = rinterface.SexpVector(o, rinterface.REALSXP)
        else:
            raise(ValueError("Nothing can be done for this array type at the moment."))
    elif isinstance(o, bool):
        res = rinterface.SexpVector([o, ], rinterface.LGLSXP)
    elif isinstance(o, int) or isinstance(o, long):
        # special case for NA_Logical
        if o is rinterface.NA_Logical:
            res = rinterface.SexpVector([o, ], rinterface.LGLSXP)
        else:
            res = rinterface.SexpVector([o, ], rinterface.INTSXP)
    elif isinstance(o, float):
        res = rinterface.SexpVector([o, ], rinterface.REALSXP)
    elif isinstance(o, str):
        res = rinterface.SexpVector([o, ], rinterface.STRSXP)
    elif isinstance(o, unicode):
        res = rinterface.SexpVector([o, ], rinterface.STRSXP)
    elif isinstance(o, list):
        res = r.list(*[conversion.ri2py(conversion.py2ri(x)) for x in o])
    elif isinstance(o, complex):
        res = rinterface.SexpVector([o, ], rinterface.CPLXSXP)
    else:
        raise(ValueError("Nothing can be done for the type %s at the moment." %(type(o))))
    return res

conversion.py2ri = default_py2ri


def default_py2ro(o):
    """ Convert any Python object to an robject.

    :param o: object
    :rtype: :class:`rpy2.robjects.RObject` (and subclasses)
    """
    res = conversion.py2ri(o)
    return conversion.ri2py(res)

conversion.py2ro = default_py2ro



class Formula(RObjectMixin, rinterface.Sexp):

    def __init__(self, formula, environment = _globalenv):
        if isinstance(formula, str):
            inpackage = rinterface.baseenv["::"]
            asformula = inpackage(rinterface.StrSexpVector(['stats', ]), 
                                  rinterface.StrSexpVector(['as.formula', ]))
            formula = rinterface.SexpVector(rinterface.StrSexpVector([formula, ]))
            robj = asformula(formula,
                             env = environment)
        else:
            robj = formula
        super(Formula, self).__init__(robj)
        
    def getenvironment(self):
        """ Get the environment in which the formula is finding its symbols."""
        res = self.do_slot(".Environment")
        res = conversion.ri2py(res)
        return res

    def setenvironment(self, val):
        """ Set the environment in which a formula will find its symbols."""
        if not isinstance(val, rinterface.SexpEnvironment):
            raise ValueError("The environment must be an instance of" +
                             " rpy2.rinterface.Sexp.environment")
        self.do_slot_assign(".Environment", val)

    environment = property(getenvironment, setenvironment,
                           "R environment in which the formula will look for" +
                           " its variables.")

    
class R(object):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            rinterface.initr()
            cls._instance = object.__new__(cls)
        return cls._instance
        
    def __getattribute__(self, attr):
        try:
            return super(R, self).__getattribute__(attr)
        except AttributeError, ae:
            orig_ae = ae

        try:
            return self.__getitem__(attr)
        except LookupError, le:
            raise orig_ae

    def __getitem__(self, item):
        res = _globalenv.get(item)
        res = conversion.ri2py(res)
        res.__rname__ = item
        return res

    #FIXME: check that this is properly working
    def __cleanup__(self):
        rinterface.endEmbeddedR()
        del(self)

    def __str__(self):
        s = super(R, self).__str__()
        s += os.linesep
        version = self["version"]
        tmp = [n+': '+val[0] for n, val in itertools.izip(version.names, version)]
        s += str.join(os.linesep, tmp)
        return s

    def __call__(self, string):
        p = rinterface.parse(string)
        res = self.eval(p)
        return res

r = R()

globalenv = conversion.ri2py(_globalenv)
baseenv = conversion.ri2py(rinterface.baseenv)
emptyenv = conversion.ri2py(rinterface.emptyenv)
