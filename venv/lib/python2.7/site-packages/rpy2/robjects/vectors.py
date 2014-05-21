from rpy2.robjects.robject import RObjectMixin, RObject
import rpy2.rinterface as rinterface
#import rpy2.robjects.conversion as conversion
import conversion

import rpy2.rlike.container as rlc

import sys, copy, os, itertools, math
import time
from datetime import datetime
from time import struct_time, mktime, tzname
from operator import attrgetter

from rpy2.rinterface import Sexp, SexpVector, ListSexpVector, StrSexpVector, \
    IntSexpVector, BoolSexpVector, ComplexSexpVector, FloatSexpVector, \
    R_NilValue, NA_Real, NA_Integer, NA_Character, NA_Logical, NULL, MissingArg

globalenv_ri = rinterface.globalenv
baseenv_ri = rinterface.baseenv
utils_ri = rinterface.baseenv['as.environment'](rinterface.StrSexpVector(("package:utils", )))

class ExtractDelegator(object):
    """ Delegate the R 'extraction' ("[") and 'replacement' ("[<-")
    of items in a vector
    or vector-like object. This can help making syntactic
    niceties possible."""
    
    _extractfunction = rinterface.baseenv['[']
    _replacefunction = rinterface.baseenv['[<-']

    def __init__(self, parent):
        self._parent = parent
        
    def __call__(self, *args, **kwargs):
        """ Subset the "R-way.", using R's "[" function. 
           In a nutshell, R indexing differs from Python indexing on:

           - indexing can be done with integers or strings (that are 'names')

           - an index equal to TRUE will mean everything selected
             (because of the recycling rule)

           - integer indexing starts at one

           - negative integer indexing means exclusion of the given integers

           - an index is itself a vector of elements to select
        """

        conv_args = list(None for x in xrange(len(args)))
        for i, x in enumerate(args):
            if x is MissingArg:
                conv_args[i] = x
            else:
                conv_args[i] = conversion.py2ro(x)
        kwargs = copy.copy(kwargs)
        for k, v in kwargs.itervalues():
            kwargs[k] = conversion.py2ro(v)
        fun = self._extractfunction
        conv_args.insert(0, self._parent)
        res = fun(*conv_args, **kwargs)
        res = conversion.py2ro(res)
        return res

    def __getitem__(self, item):
        fun = self._extractfunction
        args = rlc.TaggedList(item)
        for i, (k, v) in enumerate(args.iteritems()):
            if v is MissingArg:
                continue
            args[i] = conversion.py2ro(v)
        args.insert(0, self._parent)
        res = fun.rcall(args.items(),
                        globalenv_ri)
        res = conversion.py2ro(res)
        return res

    def __setitem__(self, item, value):
        """ Assign a given value to a given index position in the vector.
        The index position can either be:
        - an int: x[1] = y
        - a tuple of ints: x[1, 2, 3] = y
        - an iteritem-able object (such as a dict): x[{'i': 1}] = y
        """
        fun = self._replacefunction
        if type(item) is tuple:
            args = list([None, ] * (len(item)+2))
            for i, v in enumerate(item):
                if v is MissingArg:
                    continue
                args[i+1] = conversion.py2ro(v)
            args[-1] = conversion.py2ro(value)
            args[0] = self._parent
            res = fun(*args)
        elif (type(item) is dict) or (type(item) is rlc.TaggedList):
            args = rlc.TaggedList.from_iteritems(item)
            for i, (k, v) in enumerate(args.iteritems()):
                args[i] = conversion.py2ro(v)
            args.append(conversion.py2ro(value), tag = None)
            args.insert(0, self._parent, tag = None)
            res = fun.rcall(tuple(args.iteritems()),
                            globalenv_ri)
        else:
            args = [self._parent,
                    conversion.py2ro(item),
                    conversion.py2ro(value)]
            res = fun(*args)
        #FIXME: check refcount and copying
        self._parent.__sexp__ = res.__sexp__


class DoubleExtractDelegator(ExtractDelegator):
    """ Delegate the R 'extraction' ("[[") and "replacement" ("[[<-")
    of items in a vector
    or vector-like object. This can help making syntactic
    niceties possible."""
    _extractfunction = rinterface.baseenv['[[']
    _replacefunction = rinterface.baseenv['[[<-']


    
class VectorOperationsDelegator(object):
    """
    Delegate operations such as __getitem__, __add__, etc...
    to the corresponding R function.
    This permits a convenient coexistence between
    operators on Python sequence object with their R conterparts.
    """

    def __init__(self, parent):
        """ The parent in expected to inherit from Vector. """
        self._parent = parent

    def __add__(self, x):
        res = globalenv_ri.get("+")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __sub__(self, x):
        res = globalenv_ri.get("-")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __mul__(self, x):
        res = globalenv_ri.get("*")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __pow__(self, x):
        res = globalenv_ri.get("^")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __div__(self, x):
        res = globalenv_ri.get("/")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __divmod__(self, x):
        res = globalenv_ri.get("%%")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __or__(self, x):
        res = globalenv_ri.get("|")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __and__(self, x):
        res = globalenv_ri.get("&")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    # Comparisons

    def __lt__(self, x):
        res = globalenv_ri.get("<")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __le__(self, x):
        res = globalenv_ri.get("<=")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __eq__(self, x):
        res = globalenv_ri.get("==")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __ne__(self, x):
        res = globalenv_ri.get("!=")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __gt__(self, x):
        res = globalenv_ri.get(">")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)

    def __ge__(self, x):
        res = globalenv_ri.get(">=")(self._parent, conversion.py2ri(x))
        return conversion.ri2py(res)
    
    # 
    def __neg__(self):
        res = globalenv_ri.get("-")(self._parent)
        return res

    def __contains__(self, what):
        res = globalenv_ri.get("%in%")(self._parent, what)
        return res


class Vector(RObjectMixin, SexpVector):
    """ Vector(seq) -> Vector.

    The parameter 'seq' can be an instance inheriting from
    rinterface.SexpVector, or an arbitrary Python object.
    In the later case, a conversion will be attempted using
    conversion.py2ri().
    
    R vector-like object. Items can be accessed with:

    - the method "__getitem__" ("[" operator)

    - the delegators rx or rx2 

"""
    _sample = rinterface.baseenv['sample']

    def __init__(self, o):
        if not isinstance(o, SexpVector):
            o = conversion.py2ri(o)
        super(Vector, self).__init__(o)
        self.ro = VectorOperationsDelegator(self)
        self.rx = ExtractDelegator(self)
        self.rx2 = DoubleExtractDelegator(self)

    def __add__(self, x):
        res = baseenv_ri.get("c")(self, conversion.py2ri(x))
        res = conversion.ri2py(res)
        return res

    def __getitem__(self, i):
        res = super(Vector, self).__getitem__(i)
        
        if isinstance(res, Sexp):
            res = conversion.ri2py(res)
        return res

    def __setitem__(self, i, value):
        value = conversion.py2ri(value)
        res = super(Vector, self).__setitem__(i, value)

    def __getslice__(self, i, j):
        res = super(Vector, self).__getslice__(i, j)
        if isinstance(res, Sexp):
            res = conversion.ri2py(res)
        return res

    def _names_get(self):
        res = baseenv_ri.get('names')(self)
        res = conversion.ri2py(res)
        return res

    def _names_set(self, value):
        res = globalenv_ri.get("names<-")(self, conversion.py2ro(value))
        self.__sexp__ = res.__sexp__

    names = property(_names_get, _names_set, 
                     "Names for the items in the vector.")

    def iteritems(self):
        """ iterate over names and values """
        if self.names.rsame(R_NilValue):
            it_names = itertools.cycle((None, ))
        else:
            it_names = iter(self.names)
        it_self  = iter(self)
        for v, k in zip(it_self, it_names):
            yield (k, v)

    def sample(self, n, replace = False, probabilities = None):
        """ Draw a sample of size n from the vector. 
        If 'replace' is True, the sampling is done with replacement.
        The optional argument 'probabilities' can indicate sampling probabilities. """

        assert isinstance(n, int)
        assert isinstance(replace, bool)
        if probabilities is not None:
            probabilities = FloatVector(probabilities)
        res = self._sample(self, IntVector((n,)), 
                           replace = BoolVector((replace, )),
                           prob = probabilities)
        res = conversion.ri2py(res)
        return res

    def __repr_content__(self):
        def p_str(x, max_width = 8):
            max_width = int(max_width)
            if x is NA_Real or x is NA_Integer or x is NA_Character or x is NA_Logical:
                res = repr(x)
            elif isinstance(x, long) or isinstance(x, int):
                res = '%8i' %x
            elif isinstance(x, float):
                res = '%8f' %x
            else:
                if isinstance(x, str):
                    x = x.__repr__()
                else:
                    x = type(x).__name__    
                if len(x) < max_width:
                    res = x
                else:
                    res = "%s..." % (str(x[ : (max_width - 3)]))
            return res

        l = len(self)
        if l < 7:
            s = '[' + \
                ', '.join((p_str(elt, max_width = math.floor(52 / l)) for elt in self[ : 8])) +\
                ']'
        else:
            s = '[' + \
                ', '.join((p_str(elt) for elt in self[ : 3])) + ', ..., ' + \
                ', '.join((p_str(elt) for elt in self[-3 : ])) + \
                ']'
        return s

    def __repr__(self):        
        return super(Vector, self).__repr__() + os.linesep + \
            self.__repr_content__()
                          
#name alias if Python 3 (iteritems no longer existing for dict objects)
if sys.version_info[0] == 3:
    Vector.items = Vector.iteritems

class StrVector(Vector, StrSexpVector):
    """      Vector of string elements

    StrVector(seq) -> StrVector.

    The parameter 'seq' can be an instance inheriting from
    rinterface.SexpVector, or an arbitrary Python sequence.
    In the later case, all elements in the sequence should be either
    strings, or have a str() representation.
    """

    _factorconstructor = rinterface.baseenv['factor']

    def __init__(self, obj):
        obj = StrSexpVector(obj)
        super(StrVector, self).__init__(obj)

    def factor(self):
        """
        factor() -> FactorVector

        Construct a factor vector from a vector of strings. 
        
        """

        res = self._factorconstructor(self)
        return conversion.ri2py(res)

class IntVector(Vector, IntSexpVector):
    """ Vector of integer elements 
    IntVector(seq) -> IntVector.

    The parameter 'seq' can be an instance inheriting from
    rinterface.SexpVector, or an arbitrary Python sequence.
    In the later case, all elements in the sequence should be either
    integers, or have an int() representation.
    """
    _tabulate = rinterface.baseenv['tabulate']

    def __init__(self, obj):
        obj = IntSexpVector(obj)
        super(IntVector, self).__init__(obj)

    def tabulate(self, nbins = None):
        """ Like the R function tabulate,
        count the number of times integer values are found """
        if nbins is None:
            nbins = max(1, max(self))
        res = self._tabulate(self)
        return conversion.ri2py(res)

class BoolVector(Vector, BoolSexpVector):
    """ Vector of boolean (logical) elements 
    BoolVector(seq) -> BoolVector.

    The parameter 'seq' can be an instance inheriting from
    rinterface.SexpVector, or an arbitrary Python sequence.
    In the later case, all elements in the sequence should be either
    booleans, or have a bool() representation.
    """
    def __init__(self, obj):
        obj = BoolSexpVector(obj)
        super(BoolVector, self).__init__(obj)

class ComplexVector(Vector, ComplexSexpVector):
    """ Vector of complex elements 

    ComplexVector(seq) -> ComplexVector

    The parameter 'seq' can be an instance inheriting from
    rinterface.SexpVector, or an arbitrary Python sequence.
    In the later case, all elements in the sequence should be either
    complex, or have a complex() representation.
    
    """
    def __init__(self, obj):
        obj = ComplexSexpVector(obj)
        super(ComplexVector, self).__init__(obj)

class FloatVector(Vector, FloatSexpVector):
    """ Vector of float (double) elements 

    FloatVector(seq) -> FloatVector.

    The parameter 'seq' can be an instance inheriting from
    rinterface.SexpVector, or an arbitrary Python sequence.
    In the later case, all elements in the sequence should be either
    float, or have a float() representation.

    """
    def __init__(self, obj):
        obj = FloatSexpVector(obj)
        super(FloatVector, self).__init__(obj)

class FactorVector(IntVector):
    """ Vector of 'factors' 

    FactorVector(obj,
                 levels = rinterface.MissingArg,
                 labels = rinterface.MissingArg,
                 exclude = rinterface.MissingArg,
                 ordered = rinterface.MissingArg) -> FactorVector

    obj: StrVector or StrSexpVector
    levels: StrVector or StrSexpVector
    labels: StrVector or StrSexpVector (of same length as levels)
    exclude: StrVector or StrSexpVector
    ordered: boolean

    """

    _factor = baseenv_ri['factor']
    _levels = baseenv_ri['levels']
    _levels_set = baseenv_ri['levels<-']
    _nlevels = baseenv_ri['nlevels']
    _isordered = baseenv_ri['is.ordered']
    
    def __init__(self, obj, levels = rinterface.MissingArg,
                 labels = rinterface.MissingArg,
                 exclude = rinterface.MissingArg,
                 ordered = rinterface.MissingArg):
        if not isinstance(obj, Sexp):
            obj = StrSexpVector(obj)
        res = self._factor(obj,
                           levels = levels,
                           labels = labels,
                           exclude = exclude,
                           ordered = ordered)
        self.__sexp__ = res.__sexp__
        self.ro = VectorOperationsDelegator(self)
        self.rx = ExtractDelegator(self)
        self.rx2 = DoubleExtractDelegator(self)

    def __levels_get(self):
        res = self._levels(self)
        return conversion.ri2py(res)
    def __levels_set(self, value):
        res = self._levels_set(self, conversion.py2ro(value))
        self.__sexp__ = res.__sexp__

    levels = property(__levels_get, __levels_set)

    def __nlevels_get(self):
        res = self._nlevels(self)
        return res[0]
    nlevels = property(__nlevels_get, None, None, "number of levels ")

    def __isordered_get(self):
        res = self._isordered(self)
        return res[0]
    isordered = property(__isordered_get, None, None,
                         "are the levels in the factor ordered ?")

    def iter_labels(self):
        """ Iterate the over the labels, that is iterate over
        the items returning associated label for each item """
        levels = self.levels
        for x in self:
            yield levels[x-1]

class ListVector(Vector, ListSexpVector):
    """ R list (vector of arbitray elements)

    ListVector(iteritemable) -> ListVector.

    The parameter 'iteritemable' can be any object inheriting from 
    rpy2.rlike.container.TaggedList, rpy2.rinterface.SexpVector of type VECSXP,
    or dict.

    """
    _vector = rinterface.baseenv['vector']

    def __init__(self, tlist):
        if isinstance(tlist, rinterface.SexpVector):
            if tlist.typeof != rinterface.VECSXP:
                raise ValueError("tlist should of typeof VECSXP")
            super(ListVector, self).__init__(tlist)
        elif isinstance(tlist, rlc.TaggedList):
            kv = [(k, conversion.py2ri(v)) for k,v in tlist.iteritems()]
            kv = tuple(kv)
            df = baseenv_ri.get("list").rcall(kv, globalenv_ri)
            super(ListVector, self).__init__(df)
        elif hasattr(tlist, "__iter__"):
            if not callable(tlist.__iter__):
                raise ValueError("tlist should have a /method/ __iter__ (not an attribute)")
            kv = [(str(k), conversion.py2ri(tlist[k])) for k in tlist]
            kv = tuple(kv)
            df = baseenv_ri.get("list").rcall(kv, globalenv_ri)
            super(ListVector, self).__init__(df)
        else:
            raise ValueError("tlist can be either "+
                             "an iter-able " +
                             " or an instance of rpy2.rinterface.SexpVector" +
                             " of type VECSXP, or a Python dict.")

    def __repr__(self):        
        res = []
        if len(self) < 7:
            for i, x in enumerate(self):
                if isinstance(x, ListVector):
                    res.append(super(ListVector, self).__repr__())
                else:
                    try:
                        name = self.names[i]
                    except TypeError, te:
                        name = '<no name>'
                    res.append("  %s: %s%s  %s" %(name,
                                                  type(x),
                                                  os.linesep,
                                                  x.__repr__()))
        else:
            for i, x in enumerate(self[:3]):
                if isinstance(x, ListVector):
                    res.append(super(ListVector, self).__repr__())
                else:
                    try:
                        name = self.names[i]
                    except TypeError, te:
                        name = '<no name>'
                    res.append("  %s: %s%s  %s" %(name,
                                                  type(x),
                                                  os.linesep,
                                                  x.__repr__()))
            res.append('  ...')
            for i, x in enumerate(self[-3:]):
                if isinstance(x, ListVector):
                    res.append(super(ListVector, self).__repr__())
                else:
                    try:
                        name = self.names[i]
                    except TypeError, te:
                        name = '<no name>'
                    res.append("  %s: %s%s  %s" %(name,
                                                  type(x),
                                                  os.linesep,
                                                  x.__repr__()))
        res = super(ListVector, self).__repr__() + os.linesep + \
            os.linesep.join(res)
        return res

    @staticmethod
    def from_length(length):
        """ Create a list of given length """
        res = ListVector._vector(StrSexpVector(("list", )), length)
        res = conversion.ri2py(res)
        return res

class DateVector(FloatVector):
    """ Vector of dates """
    pass

class POSIXt(object):
    """ POSIX time vector. This is an abstract class. """
    pass

class POSIXlt(POSIXt, Vector):
    """ Representation of dates with a 9-component structure
    (similar to Python's time.struct_time).

    POSIXlt(seq) -> POSIXlt.
        
    The constructor accepts either an R vector
    or a sequence (an object with the Python
    sequence interface) of time.struct_time objects. 
    """

    def __init__(self, seq):
        """ 
        """
        if isinstance(seq, Sexp):
            super(self, Vector)(seq)
        else:
            for elt in seq:
                if not isinstance(elt, struct_time):
                    raise ValueError('All elements must inherit from time.struct_time')
            as_posixlt = baseenv_ri['as.POSIXlt']
            origin = StrSexpVector([time.strftime("%Y-%m-%d", 
                                                  time.gmtime(0)),])
            rvec = FloatSexpVector([mktime(x) for x in seq]) 
            sexp = as_posixlt(rvec, origin = origin)
            self.__sexp__ = sexp.__sexp__

    def __getitem__(self, i):
        # "[[" operator returns the components of a time object
        # (and yes, this is confusing)
        tmp = self.rx2(i-1)
        return struct_time(*tuple(tmp))
        
class POSIXct(POSIXt, FloatVector):
    """ Representation of dates as seconds since Epoch.
    This form is preferred to POSIXlt for inclusion in a DataFrame.

    POSIXlt(seq) -> POSIXlt.
    
    The constructor accepts either an R vector floats
    or a sequence (an object with the Python
    sequence interface) of time.struct_time objects.
    """

    _as_posixct = baseenv_ri['as.POSIXct']
    _ISOdatetime = baseenv_ri['ISOdatetime']

    def __init__(self, seq):
        """ Create a POSIXct from either an R vector or a sequence
        of Python dates.
        """

        if isinstance(seq, Sexp):
            super(FloatVector, self).__init__(seq)
        elif isinstance(seq[0], struct_time):
            sexp = POSIXct.sexp_from_struct_time(seq)
            self.__sexp__ = sexp.__sexp__            
        elif isinstance(seq[0], datetime):
            sexp = POSIXct.sexp_from_datetime(seq)
            self.__sexp__ = sexp.__sexp__                        
        else:
            raise ValueError('All elements must inherit from time.struct_time or datetime.datetime.')

    @staticmethod
    def _sexp_from_seq(seq, tz_info_getter, isodatetime_columns):
        """ return a POSIXct vector from a sequence of time.struct_time 
        elements. """
        tz_count = 0
        tz_info = None
        for elt in seq:
            tmp = tz_info_getter(elt)
            if tz_info is None:
                tz_info = tmp
                tz_count = 1
            elif tz_info == tmp:
                tz_count += 1
            else:
                # different time zones
                #FIXME: create a list of time zones with tz_count times
                # tz_info, add the current tz_info and append further.
                raise ValueError("Sequences of dates with different time zones not yet allowed.")

        if tz_info is None:
            tz_info = tzname[0]
        # We could use R's as.POSIXct instead of ISOdatetime
        # since as.POSIXct is used by it anyway, but the overall
        # interface for dates and conversion between formats
        # is not exactly straightforward. Someone with more
        # time should look into this.

        d = isodatetime_columns(seq)
        sexp = POSIXct._ISOdatetime(*d, tz = StrSexpVector((tz_info, )))
        return sexp


    @staticmethod
    def sexp_from_struct_time(seq):
        def f(seq):
            return [IntVector([x.tm_year for x in seq]),
                    IntVector([x.tm_mon for x in seq]),
                    IntVector([x.tm_mday for x in seq]),
                    IntVector([x.tm_hour for x in seq]),
                    IntVector([x.tm_min for x in seq]),
                    IntVector([x.tm_sec for x in seq])]
        return POSIXct._sexp_from_seq(seq, lambda elt: time.tzname[0], f)
    
    @staticmethod
    def sexp_from_datetime(seq):
        """ return a POSIXct vector from a sequence of
        datetime.datetime elements. """
        def f(seq):
            return [IntVector([x.year for x in seq]),
                    IntVector([x.month for x in seq]),
                    IntVector([x.day for x in seq]),
                    IntVector([x.hour for x in seq]),
                    IntVector([x.minute for x in seq]),
                    IntVector([x.second for x in seq])]
        
        return POSIXct._sexp_from_seq(seq, attrgetter('tzinfo'), f)
       
        
class Array(Vector):
    """ An R array """
    _dimnames_get = baseenv_ri['dimnames']
    _dimnames_set = baseenv_ri['dimnames<-']
    _dim_get = baseenv_ri['dim']
    _dim_set = baseenv_ri['dim<-']
    _isarray = baseenv_ri['is.array']

    def __init__(self, obj):
        super(Array, self).__init__(obj)
        #import pdb; pdb.set_trace()
        if not self._isarray(self)[0]:
            raise(TypeError("The object must be representing an R array"))

    def __dim_get(self):
        res = self._dim_get(self)
        res = conversion.ri2py(res)
        return res

    def __dim_set(self, value):
        value = conversion.py2ro(value)
        res = self._dim_set(self, value)
            #FIXME: not properly done
        raise(Exception("Not yet implemented"))

    dim = property(__dim_get, __dim_set, 
                   "Get or set the dimension of the array.")

    def __dimnames_get(self):
        """ Return a list of name vectors
        (like the R function 'dimnames' does)."""

        res = self._dimnames_get(self)
        res = conversion.ri2py(res)
        return res

    def __dimnames_set(self, value):
        """ Set list of name vectors
        (like the R function 'dimnames' does)."""

        value = conversion.ri2py(value)
        res = self._dimnames_set(self, value)        
        self.__sexp__ = res.__sexp__
        
    names = property(__dimnames_get, __dimnames_set, None, 
                     "names associated with the dimension.")
    dimnames = names


class Matrix(Array):
    """ An R matrix """
    _transpose = baseenv_ri['t']
    _rownames = baseenv_ri['rownames']
    _colnames = baseenv_ri['colnames']
    _dot = baseenv_ri['%*%']
    _crossprod = baseenv_ri['crossprod']
    _tcrossprod = baseenv_ri['tcrossprod']
    _svd = baseenv_ri['svd']
    _eigen = baseenv_ri['eigen']

    def __nrow_get(self):
        """ Number of rows.
        :rtype: integer """
        return self.dim[0]
    nrow = property(__nrow_get, None, None, "Number of rows")

    def __ncol_get(self):
        """ Number of columns.
        :rtype: integer """
        return self.dim[1]
    ncol = property(__ncol_get, None, None, "Number of columns")

    def __rownames_get(self):
        """ Row names
        
        :rtype: SexpVector
        """
        res = self._rownames(self)
        return conversion.ri2py(res)
    def __rownames_set(self, rn):
        if isinstance(rn, StrSexpVector):
            if len(rn) != self.nrow:
                raise ValueError('Invalid length.')
            if self.dimnames is NULL:
                dn = ListVector.from_length(2)
                dn[0] = rn
                self.do_slot_assign('dimnames', dn)
            else:
                dn = self.dimnames
                dn[0] = rn
        else:
            raise ValueError('The rownames attribute can only be an R string vector.')
    rownames = property(__rownames_get, __rownames_set, None, "Row names")

            

    def __colnames_get(self):
        """ Column names

        :rtype: SexpVector
        """
        res = self._colnames(self)
        return conversion.ri2py(res)
    def __colnames_set(self, cn):
        if isinstance(cn, StrSexpVector):
            if len(cn) != self.ncol:
                raise ValueError('Invalid length.')
            if self.dimnames is NULL:
                dn = ListVector.from_length(2)
                dn[1] = cn
                self.do_slot_assign('dimnames', dn)
            else:
                dn = self.dimnames
                dn[1] = cn
        else:
            raise ValueError('The colnames attribute can only be an R string vector.')
    colnames = property(__colnames_get, __colnames_set, None, "Column names")
        
    def transpose(self):
        """ transpose the matrix """
        res = self._transpose(self)
        return conversion.ri2py(res)

    def crossprod(self, m):
        """ crossproduct X'.Y"""
        res = self._crossprod(self, conversion.ri2py(m))
        return conversion.ri2py(res)

    def tcrossprod(self, m):
        """ crossproduct X.Y'"""
        res = self._tcrossprod(self, m)
        return conversion.ri2py(res)

    def svd(self, nu = None, nv = None, linpack = False):
        """ SVD decomposition.
        If nu is None, it is given the default value min(tuple(self.dim)).
        If nv is None, it is given the default value min(tuple(self.dim)).
        """
        if nu is None:
            nu = min(tuple(self.dim))
        if nv is None:
            nv = min(tuple(self.dim))
        res = self._svd(self, nu = nu, nv = nv, LINPACK = False)
        return conversion.ri2py(res)

    def dot(self, m):
        """ Matrix multiplication """
        res = self._dot(self, m)
        return conversion.ri2py(res)

    def eigen(self):
        """ Eigen values """
        res = self._eigen(self)
        return conversion.ri2py(res)

class DataFrame(ListVector):
    """ R 'data.frame'.
    """
    _dataframe_name = rinterface.StrSexpVector(('data.frame',))
    _read_csv  = utils_ri['read.csv']
    _write_table = utils_ri['write.table']
    _cbind     = rinterface.baseenv['cbind.data.frame']
    _rbind     = rinterface.baseenv['rbind.data.frame']
    _is_list   = rinterface.baseenv['is.list']
    
    def __init__(self, obj):
        """ Create a new data frame.

        :param obj: object inheriting from rpy2.rinterface.SexpVector,
                    or inheriting from TaggedList
                    or a mapping name -> value
        """
        if isinstance(obj, rinterface.SexpVector):
            if obj.typeof != rinterface.VECSXP:
                raise ValueError("obj should of typeof VECSXP"+\
                                     " (and we get %s)" % rinterface.str_typeint(obj.typeof))
            if self._is_list(obj)[0] or \
                    globalenv_ri.get('inherits')(obj, self._dataframe_name)[0]:
                #FIXME: is it really a good idea to pass R lists
                # to the constructor ?
                super(DataFrame, self).__init__(obj)
            else:
                raise ValueError(
            "When passing R objects to build a DataFrame," +\
                " the R object must be a list or inherit from" +\
                " the R class 'data.frame'")
        elif isinstance(obj, rlc.TaggedList):
            kv = [(k, conversion.py2ri(v)) for k,v in obj.items()]
            kv = tuple(kv)
            df = baseenv_ri.get("data.frame").rcall(kv, globalenv_ri)
            super(DataFrame, self).__init__(df)
        else:
            try:
                kv = [(str(k), conversion.py2ri(obj[k])) for k in obj]
            except TypeError:
                raise ValueError("obj can be either "+
                                 "an instance of an iter-able class" +
                                 "(such a Python dict, rpy2.rlike.container OrdDict" +
                                 " or an instance of rpy2.rinterface.SexpVector" +
                                 " of type VECSXP")
            
            df = baseenv_ri.get("data.frame").rcall(tuple(kv), globalenv_ri)
            super(DataFrame, self).__init__(df)
    
    def _get_nrow(self):
        """ Number of rows. 
        :rtype: integer """
        return baseenv_ri["nrow"](self)[0]
    nrow = property(_get_nrow, None, None)

    def _get_ncol(self):
        """ Number of columns.
        :rtype: integer """
        return baseenv_ri["ncol"](self)[0]
    ncol = property(_get_ncol, None, None)
    
    def _get_rownames(self):
        res = baseenv_ri["rownames"](self)
        return conversion.ri2py(res)

    def _set_rownames(self, rownames):
        res = baseenv_ri["rownames<-"](self, conversion.py2ri(rownames))
        self.__sexp__ = res.__sexp__

    rownames = property(_get_rownames, _set_rownames, None, 
                        "Row names")

    def _get_colnames(self):
        res = baseenv_ri["colnames"](self)
        return conversion.ri2py(res)

    def _set_colnames(self, colnames):
        res = baseenv_ri["colnames<-"](self, conversion.py2ri(colnames))
        self.__sexp__ = res.__sexp__
        
    colnames = property(_get_colnames, _set_colnames, None)

    def __getitem__(self, i):
        # Make sure this is not a List returned
        # FIXME: should this be optimzed ?
        tmp = super(DataFrame, self).__getitem__(i)
        if tmp.typeof == rinterface.VECSXP:
            return DataFrame(tmp)
        else:
            return conversion.ri2py(tmp)

    def cbind(self, *args, **kwargs):
        """ bind objects as supplementary columns """
        new_args   = [self, ] + [conversion.ri2py(x) for x in args]
        new_kwargs = dict([(k, conversion.ri2py(v)) for k,v in kwargs.iteritems()])
        res = self._cbind(*new_args, **new_kwargs)
        return conversion.ri2py(res)

    def rbind(self, *args, **kwargs):
        """ bind objects as supplementary rows """
        new_args   = [conversion.ri2py(x) for x in args]
        new_kwargs = dict([(k, conversion.ri2py(v)) for k,v in kwargs.iteritems()])
        res = self._rbind(self, *new_args, **new_kwargs)
        return conversion.ri2py(res)


    @staticmethod
    def from_csvfile(path, header = True, sep = ",",
                     quote = "\"", dec = ".", 
                     row_names = rinterface.MissingArg,
                     col_names = rinterface.MissingArg,
                     fill = True, comment_char = "",
                     as_is = False):
        """ Create an instance from data in a .csv file. 

        path         : string with a path 
        header       : boolean (heading line with column names or not)
        sep          : separator character
        quote        : quote character
        row_names    : column name, or column index for column names (warning: indexing starts at one in R)
        fill         : boolean (fill the lines when less entries than columns)
        comment_char : comment character
        as_is        : boolean (keep the columns of strings as such, or turn them into factors) 
        """
        path = conversion.py2ro(path)
        header = conversion.py2ro(header)
        sep = conversion.py2ro(sep)
        quote = conversion.py2ro(quote)
        dec = conversion.py2ro(dec)
        if row_names is not rinterface.MissingArg:
            row_names = conversion.py2ro(row_names)
        if col_names is not rinterface.MissingArg:
            col_names = conversion.py2ro(col_names)
        fill = conversion.py2ro(fill)
        comment_char = conversion.py2ro(comment_char)
        as_is = conversion.py2ro(as_is)
        res = DataFrame._read_csv(path, 
                                  **{'header': header, 'sep': sep,
                                     'quote': quote, 'dec': dec,
                                     'row.names': row_names,
                                     'col.names': col_names,
                                     'fill': fill,
                                     'comment.char': comment_char,
                                     'as.is': as_is})
        res = conversion.ri2py(res)
        return res

    def to_csvfile(self, path, quote = True, sep = ",", eol = os.linesep, na = "NA", dec = ".", 
                   row_names = True, col_names = True, qmethod = "escape", append = False):
        """ Save the data into a .csv file. 

        path         : string with a path 
        quote        : quote character
        sep          : separator character
        eol          : end-of-line character(s)
        na           : string for missing values
        dec          : string for decimal separator
        row_names    : boolean (save row names, or not)
        col_names    : boolean (save column names, or not)
        comment_char : method to 'escape' special characters
        append       : boolean (append if the file in the path is already existing, or not)
        """
        path = conversion.py2ro(path)
        append = conversion.py2ro(append)
        sep = conversion.py2ro(sep)
        eol = conversion.py2ro(eol)
        na = conversion.py2ro(na)
        dec = conversion.py2ro(dec)
        row_names = conversion.py2ro(row_names)
        col_names = conversion.py2ro(col_names)
        qmethod = conversion.py2ro(qmethod)
        res = self._write_table(self, **{'file': path, 'quote': quote, 'sep': sep, 
                                         'eol': eol, 'na': na, 'dec': dec,
                                         'row.names': row_names, 
                                         'col.names': col_names, 'qmethod': qmethod, 'append': append})
        return res
    
    def iter_row(self):
        """ iterator across rows """
        for i in xrange(self.nrow):
            yield self.rx(i+1, rinterface.MissingArg)

    def iter_column(self):
        """ iterator across columns """
        for i in xrange(self.ncol):
            yield self.rx(rinterface.MissingArg, i+1)


# end of definition for DataFrame

__all__ = ['Vector', 'StrVector', 'IntVector', 'BoolVector', 'ComplexVector',
           'FloatVector', 'FactorVector', 'ListVector', 'POSIXlt', 'POSIXct',
           'Array', 'Matrix', 'DataFrame']
