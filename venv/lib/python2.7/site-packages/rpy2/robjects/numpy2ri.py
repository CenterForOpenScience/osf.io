import rpy2.robjects as ro
import rpy2.robjects.conversion as conversion
import rpy2.rinterface as rinterface
from rpy2.rinterface import SexpVector, INTSXP
import numpy

from rpy2.robjects.vectors import DataFrame, Vector, ListVector

original_conversion = conversion.py2ri

# The possible kind codes are listed at
#   http://numpy.scipy.org/array_interface.shtml
_kinds = {
    # "t" -> not really supported by numpy
    "b": rinterface.LGLSXP,
    "i": rinterface.INTSXP,
    # "u" -> special-cased below
    "f": rinterface.REALSXP,
    "c": rinterface.CPLXSXP,
    # "O" -> special-cased below
    "S": rinterface.STRSXP,
    "U": rinterface.STRSXP,
    # "V" -> special-cased below
    }

def numpy2ri(o):
    """ Augmented conversion function, converting numpy arrays into
    rpy2.rinterface-level R structures. """
    if isinstance(o, numpy.ndarray):
        if not o.dtype.isnative:
            raise(ValueError("Cannot pass numpy arrays with non-native byte orders at the moment."))

        # Most types map onto R arrays:
        if o.dtype.kind in _kinds:
            # "F" means "use column-major order"
            vec = SexpVector(o.ravel("F"), _kinds[o.dtype.kind])
            dim = SexpVector(o.shape, INTSXP)
            res = ro.r.array(vec, dim=dim)
        # R does not support unsigned types:
        elif o.dtype.kind == "u":
            raise(ValueError("Cannot convert numpy array of unsigned values -- R does not have unsigned integers."))
        # Array-of-PyObject is treated like a Python list:
        elif o.dtype.kind == "O":
            res = conversion.py2ri(list(o))
        # Record arrays map onto R data frames:
        elif o.dtype.kind == "V":
            if o.dtype.names is None:
                raise(ValueError("Nothing can be done for this numpy array type %s at the moment." % (o.dtype,)))
            df_args = []
            for field_name in o.dtype.names:
                df_args.append((field_name, 
                                conversion.py2ri(o[field_name])))
            res = ro.baseenv["data.frame"].rcall(tuple(df_args), ro.globalenv)
        # It should be impossible to get here:
        else:
            raise(ValueError("Unknown numpy array type."))
    else:
        res = ro.default_py2ri(o)
    return res





def ri2numpy(o):
    if isinstance(o, ListVector):
        res = numpy.rec.fromarrays(o, names=tuple(o.names))
    elif isinstance(o, Vector) and (type(o) != Vector):
        res = numpy.asarray(o)
    else:
        res = ro.default_ri2py(o)
    return res




def activate():
    conversion.py2ri = numpy2ri
    conversion.ri2numpy = ri2numpy 

